"""Persistent Node Core content registry."""
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

    @classmethod
    def create(cls, result: AddedContent, *, pinned: bool, source_path: str | None = None):
        return cls(result.cid, result.name, result.size, datetime.now(timezone.utc).isoformat(),
                   pinned, source_path, None, {})

class ContentRegistry:
    """Durable local index of content known to Node Core."""
    def __init__(self, storage: StorageManager):
        self.storage = storage
        self.path = storage.path("registry/content.json")
    def _load(self):
        if not self.path.exists(): return {}
        try: data=json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: raise ContentError(f"Unable to read content registry: {exc}") from exc
        return data if isinstance(data,dict) else {}
    def _save(self, records):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(records,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        temp.replace(self.path)
    def upsert(self, record):
        records=self._load(); records[record.cid]=asdict(record); self._save(records); return record
    def get(self,cid):
        value=self._load().get(cid)
        return None if value is None else ContentRecord(**value)
    def list(self): return [ContentRecord(**v) for v in self._load().values()]
    def update_pin(self,cid,pinned):
        record=self.get(cid)
        if record is not None: record.pinned=pinned; self.upsert(record)

class ContentManager:
    """Node Core content API, with durable CID records."""
    def __init__(self,kubo:KuboManager,storage:StorageManager):
        self.kubo=kubo; self.storage=storage; self.registry=ContentRegistry(storage)
    def add(self,source: str|Path,*,pin=False):
        path=Path(source).expanduser()
        try:
            result=self.kubo.add_file(path,pin=pin)
            return self.registry.upsert(ContentRecord.create(result,pinned=pin,source_path=str(path.resolve())))
        except (OSError,ValueError) as exc: raise ContentError(str(exc)) from exc
        except Exception as exc: raise ContentError(f"Unable to add content: {exc}") from exc
    def retrieve(self,cid,destination):
        target=Path(destination).expanduser()
        if target.exists() and target.is_dir(): raise ContentError("Retrieve destination must be a file path.")
        try:
            data=self.kubo.cat(cid); target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data); return target
        except (OSError,ValueError) as exc: raise ContentError(str(exc)) from exc
        except Exception as exc: raise ContentError(f"Unable to retrieve {cid}: {exc}") from exc
    def pin(self,cid):
        try: self.kubo.pin_add(cid); self.registry.update_pin(cid,True)
        except Exception as exc: raise ContentError(f"Unable to pin {cid}: {exc}") from exc
    def unpin(self,cid):
        try: self.kubo.pin_remove(cid); self.registry.update_pin(cid,False)
        except Exception as exc: raise ContentError(f"Unable to unpin {cid}: {exc}") from exc
    def pins(self):
        try: return self.kubo.pin_list()
        except Exception as exc: raise ContentError(f"Unable to list pins: {exc}") from exc
    def get(self,cid): return self.registry.get(cid)
    def records(self): return self.registry.list()
