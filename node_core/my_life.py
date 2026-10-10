"""Personal My Life / Node Blog backed by local storage and optional IPFS."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from node_core.content import ContentManager
from node_core.storage import StorageManager


@dataclass(frozen=True)
class LifeEntry:
    entry_id: str
    title: str
    text_path: str
    created_at: str
    cid: str | None = None
    pinned: bool = False


class MyLifeBlog:
    """Keep personal entries locally; add to IPFS only on explicit request."""

    def __init__(self, storage: StorageManager, content: ContentManager) -> None:
        self.storage = storage
        self.content = content
        self.entries_dir = storage.path("my-life/entries")
        self.index_path = storage.path("my-life/index.json")

    def _load(self) -> list[dict[str, Any]]:
        if not self.index_path.exists():
            return []
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unable to read My Life index: {exc}") from exc
        if not isinstance(data, list):
            raise RuntimeError("My Life index must contain a JSON list.")
        return data

    def _save(self, entries: list[dict[str, Any]]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.index_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.index_path)

    def list_entries(self) -> list[LifeEntry]:
        return [LifeEntry(**item) for item in self._load()]

    def publish_entry(self, entry_id: str) -> LifeEntry:
        """Publish and pin exactly one selected entry, preserving its local file."""
        entries = self._load()
        selected = None
        for item in entries:
            if item.get("entry_id") == entry_id:
                selected = item
                break
        if selected is None:
            raise ValueError(f"My Life entry not found: {entry_id}")

        local_path = Path(selected["text_path"])
        if not local_path.is_file():
            raise FileNotFoundError(f"My Life local entry is missing: {local_path}")

        cid = selected.get("cid")
        pinned = bool(selected.get("pinned", False))
        if cid:
            if not pinned:
                self.content.pin(cid)
                selected["pinned"] = True
        else:
            record = self.content.add(local_path, pin=True)
            selected["cid"] = record.cid
            selected["pinned"] = bool(record.pinned)

        self._save(entries)
        return LifeEntry(**selected)

    def create_entry(
        self, title: str, text: str, *, add_to_ipfs: bool = False
    ) -> LifeEntry:
        title = title.strip()
        text = text.strip()
        if not title:
            raise ValueError("Entry title cannot be empty.")
        if not text:
            raise ValueError("Entry text cannot be empty.")

        created_at = datetime.now(timezone.utc)
        entry_id = created_at.strftime("%Y%m%dT%H%M%S%fZ")
        relative_path = f"my-life/entries/{entry_id}.md"
        local_path = self.storage.write_bytes(
            relative_path,
            (f"# {title}\n\n{text}\n").encode("utf-8"),
        )

        cid = None
        pinned = False
        ipfs_error = None
        if add_to_ipfs:
            try:
                record = self.content.add(local_path, pin=True)
                cid = record.cid
                pinned = record.pinned
            except Exception as exc:
                ipfs_error = exc

        entry = LifeEntry(
            entry_id=entry_id,
            title=title,
            text_path=str(local_path),
            created_at=created_at.isoformat(),
            cid=cid,
            pinned=pinned,
        )
        entries = self._load()
        entries.append(asdict(entry))
        self._save(entries)
        if ipfs_error is not None:
            raise RuntimeError(
                "Entry was saved locally, but adding it to IPFS failed: "
                + str(ipfs_error)
            ) from ipfs_error
        return entry
