"""Persistent Node Core content registry and publication layer."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from node_core.ipfs import AddedContent, KuboManager
from node_core.storage import StorageManager


class ContentError(RuntimeError):
    """Raised when a content operation cannot be completed."""


@dataclass
class ContentRecord:
    cid: str
    name: str
    size: int
    created_at: str
    pinned: bool = False
    source_path: str | None = None
    owner_id: str | None = None
    provenance: dict[str, Any] | None = None
    published_at: str | None = None
    publication_mode: str | None = None

    @classmethod
    def create(
        cls,
        result: AddedContent,
        *,
        pinned: bool,
        source_path: str | None = None,
    ) -> "ContentRecord":
        return cls(
            cid=result.cid,
            name=result.name,
            size=result.size,
            created_at=datetime.now(timezone.utc).isoformat(),
            pinned=pinned,
            source_path=source_path,
            provenance={},
        )


@dataclass(frozen=True)
class ShareReference:
    cid: str
    ipfs_uri: str
    gateway_url: str
    path: str


class ContentRegistry:
    """Durable local index of content known to Node Core."""

    def __init__(self, storage: StorageManager) -> None:
        self.storage = storage
        self.path = storage.path("registry/content.json")

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContentError(f"Unable to read content registry: {exc}") from exc
        return data if isinstance(data, dict) else {}

    def _save(self, records: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(records, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temp.replace(self.path)

    def upsert(self, record: ContentRecord) -> ContentRecord:
        records = self._load()
        records[record.cid] = asdict(record)
        self._save(records)
        return record

    def get(self, cid: str) -> ContentRecord | None:
        value = self._load().get(cid)
        if value is None:
            return None
        return ContentRecord(**value)

    def list(self) -> list[ContentRecord]:
        return [ContentRecord(**value) for value in self._load().values()]

    def update_pin(self, cid: str, pinned: bool) -> None:
        record = self.get(cid)
        if record is not None:
            record.pinned = pinned
            self.upsert(record)

    def publish(self, cid: str, *, mode: str = "cid") -> ContentRecord:
        record = self.get(cid)
        if record is None:
            raise ContentError(f"Content is not registered: {cid}")
        record.published_at = datetime.now(timezone.utc).isoformat()
        record.publication_mode = mode
        return self.upsert(record)

    def unpublish(self, cid: str) -> ContentRecord:
        record = self.get(cid)
        if record is None:
            raise ContentError(f"Content is not registered: {cid}")
        record.published_at = None
        record.publication_mode = None
        return self.upsert(record)


class ContentManager:
    """Node Core content API, with registry and CID publication semantics."""

    def __init__(
        self,
        kubo: KuboManager,
        storage: StorageManager,
        gateway: str = "http://127.0.0.1:8080",
    ) -> None:
        self.kubo = kubo
        self.storage = storage
        self.gateway = gateway.rstrip("/")
        self.registry = ContentRegistry(storage)

    def add(self, source: str | Path, *, pin: bool = False) -> ContentRecord:
        path = Path(source).expanduser()
        try:
            result = self.kubo.add_file(path, pin=pin)
            record = ContentRecord.create(
                result,
                pinned=pin,
                source_path=str(path.resolve()),
            )
            return self.registry.upsert(record)
        except (OSError, ValueError) as exc:
            raise ContentError(str(exc)) from exc
        except Exception as exc:
            raise ContentError(f"Unable to add content: {exc}") from exc

    def retrieve(self, cid: str, destination: str | Path) -> Path:
        target = Path(destination).expanduser()
        if target.exists() and target.is_dir():
            raise ContentError("Retrieve destination must be a file path.")
        try:
            data = self.kubo.cat(cid)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            return target
        except (OSError, ValueError) as exc:
            raise ContentError(str(exc)) from exc
        except Exception as exc:
            raise ContentError(f"Unable to retrieve {cid}: {exc}") from exc

    def pin(self, cid: str) -> None:
        try:
            self.kubo.pin_add(cid)
            self.registry.update_pin(cid, True)
        except Exception as exc:
            raise ContentError(f"Unable to pin {cid}: {exc}") from exc

    def unpin(self, cid: str) -> None:
        try:
            self.kubo.pin_remove(cid)
            self.registry.update_pin(cid, False)
        except Exception as exc:
            raise ContentError(f"Unable to unpin {cid}: {exc}") from exc

    def publish(self, cid: str, *, pin: bool = True) -> ContentRecord:
        """Publish a known CID as a Node Core CID publication.

        This is intentionally not IPNS publication. Identity and key-backed
        naming belong to the future identity layer.
        """
        record = self.registry.get(cid)
        if record is None:
            raise ContentError(f"Content is not registered: {cid}")
        if pin and not record.pinned:
            self.pin(cid)
            record = self.registry.get(cid)
            if record is None:
                raise ContentError(f"Content record disappeared: {cid}")
        return self.registry.publish(cid, mode="cid")

    def unpublish(self, cid: str) -> ContentRecord:
        return self.registry.unpublish(cid)

    def share(self, cid: str) -> ShareReference:
        record = self.registry.get(cid)
        if record is None:
            raise ContentError(f"Content is not registered: {cid}")
        return ShareReference(
            cid=cid,
            ipfs_uri=f"ipfs://{cid}",
            gateway_url=f"{self.gateway}/ipfs/{cid}",
            path=f"/ipfs/{cid}",
        )

    def pins(self) -> dict[str, dict[str, str]]:
        try:
            return self.kubo.pin_list()
        except Exception as exc:
            raise ContentError(f"Unable to list pins: {exc}") from exc

    def get(self, cid: str) -> ContentRecord | None:
        return self.registry.get(cid)

    def records(self) -> list[ContentRecord]:
        return self.registry.list()
