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
        if add_to_ipfs:
            record = self.content.add(local_path, pin=True)
            cid = record.cid
            pinned = record.pinned

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
        return entry
