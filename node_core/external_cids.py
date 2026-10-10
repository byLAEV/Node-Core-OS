from __future__ import annotations

"""Persistent library of references to externally known IPFS content."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from node_core.ipfs import KuboManager, KuboError
from node_core.storage import StorageManager


class ExternalCIDError(RuntimeError):
    """Raised when an external CID reference operation fails."""


@dataclass
class ExternalCIDReference:
    reference_id: str
    cid: str
    description: str
    source_node: str
    added_at: str
    notes: str = ""


class ExternalCIDLibrary:
    """Stores user-managed CID references separately from locally added content."""

    def __init__(self, storage: StorageManager, kubo: KuboManager) -> None:
        self.storage = storage
        self.kubo = kubo
        self.path = storage.path("registry/external-cids.json")

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExternalCIDError(f"Unable to read external CID library: {exc}") from exc
        if not isinstance(data, dict):
            raise ExternalCIDError("External CID library must contain a JSON object.")
        records: dict[str, dict[str, Any]] = {}
        for reference_id, value in data.items():
            if not isinstance(value, dict):
                raise ExternalCIDError("External CID library contains an invalid record.")
            try:
                records[reference_id] = asdict(ExternalCIDReference(**value))
            except (TypeError, ValueError) as exc:
                raise ExternalCIDError(
                    f"External CID library record '{reference_id}' is invalid."
                ) from exc
        return records

    def _save(self, records: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(records, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def _validate_cid(cid: str) -> str:
        value = cid.strip()
        try:
            KuboManager._validate_cid(value)
        except (AttributeError, ValueError) as exc:
            raise ExternalCIDError(f"Invalid or unsupported CID: {cid}") from exc
        if not value:
            raise ExternalCIDError("CID cannot be empty.")
        return value

    def add(
        self,
        cid: str,
        description: str,
        *,
        source_node: str = "",
        notes: str = "",
    ) -> ExternalCIDReference:
        value = self._validate_cid(cid)
        description = description.strip()
        if not description:
            raise ExternalCIDError("Description cannot be empty.")
        reference = ExternalCIDReference(
            reference_id=uuid4().hex,
            cid=value,
            description=description,
            source_node=source_node.strip(),
            added_at=datetime.now(timezone.utc).isoformat(),
            notes=notes.strip(),
        )
        records = self._load()
        records[reference.reference_id] = asdict(reference)
        self._save(records)
        return reference

    def list(self) -> list[ExternalCIDReference]:
        records = self._load()
        references = [ExternalCIDReference(**value) for value in records.values()]
        return sorted(references, key=lambda item: item.added_at, reverse=True)

    def get(self, reference_id: str) -> ExternalCIDReference | None:
        value = self._load().get(reference_id)
        return ExternalCIDReference(**value) if value is not None else None

    def search(self, query: str) -> list[ExternalCIDReference]:
        term = query.strip().casefold()
        if not term:
            raise ExternalCIDError("Search query cannot be empty.")
        return [
            reference
            for reference in self.list()
            if term in " ".join(
                (
                    reference.reference_id,
                    reference.cid,
                    reference.description,
                    reference.source_node,
                    reference.notes,
                )
            ).casefold()
        ]

    def update(
        self,
        reference_id: str,
        *,
        description: str | None = None,
        source_node: str | None = None,
        notes: str | None = None,
    ) -> ExternalCIDReference:
        records = self._load()
        value = records.get(reference_id)
        if value is None:
            raise ExternalCIDError(f"External CID reference not found: {reference_id}")
        reference = ExternalCIDReference(**value)
        if description is not None:
            if not description.strip():
                raise ExternalCIDError("Description cannot be empty.")
            reference.description = description.strip()
        if source_node is not None:
            reference.source_node = source_node.strip()
        if notes is not None:
            reference.notes = notes.strip()
        records[reference_id] = asdict(reference)
        self._save(records)
        return reference

    def remove(self, reference_id: str) -> bool:
        records = self._load()
        if reference_id not in records:
            return False
        del records[reference_id]
        self._save(records)
        return True

    def is_pinned_locally(self, cid: str) -> bool:
        value = self._validate_cid(cid)
        try:
            return value in self.kubo.pin_list()
        except Exception as exc:
            raise ExternalCIDError(f"Unable to check local pin status: {exc}") from exc

    def retrieve(self, cid: str, destination: str | Path) -> Path:
        value = self._validate_cid(cid)
        target = Path(destination).expanduser()
        if target.exists() and target.is_dir():
            raise ExternalCIDError("Retrieve destination must be a file path.")
        try:
            content = self.kubo.cat(value)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            return target
        except (OSError, ValueError, KuboError) as exc:
            raise ExternalCIDError(f"Unable to retrieve CID {value}: {exc}") from exc

    def pin(self, cid: str) -> None:
        value = self._validate_cid(cid)
        try:
            self.kubo.pin_add(value)
        except Exception as exc:
            raise ExternalCIDError(f"Unable to pin CID {value}: {exc}") from exc

    def unpin(self, cid: str) -> None:
        value = self._validate_cid(cid)
        try:
            self.kubo.pin_remove(value)
        except Exception as exc:
            raise ExternalCIDError(f"Unable to unpin CID {value}: {exc}") from exc
