"""Node Core content capabilities built over Kubo."""

from dataclasses import dataclass
from pathlib import Path

from node_core.ipfs import AddedContent, KuboManager
from node_core.storage import StorageManager


class ContentError(RuntimeError):
    """Raised when a content operation cannot be completed."""


@dataclass(frozen=True)
class ContentReference:
    cid: str
    name: str
    size: int


class ContentManager:
    """Provides the Node Core content API without exposing Kubo details."""

    def __init__(self, kubo: KuboManager, storage: StorageManager) -> None:
        self.kubo = kubo
        self.storage = storage

    def add(self, source: str | Path, *, pin: bool = False) -> ContentReference:
        path = Path(source).expanduser()
        try:
            result: AddedContent = self.kubo.add_file(path, pin=pin)
        except (OSError, ValueError) as exc:
            raise ContentError(str(exc)) from exc
        except Exception as exc:
            raise ContentError(f"Unable to add content: {exc}") from exc
        return ContentReference(result.cid, result.name, result.size)

    def retrieve(self, cid: str, destination: str | Path) -> Path:
        target = Path(destination).expanduser()
        if target.exists() and target.is_dir():
            raise ContentError("Retrieve destination must be a file path.")
        try:
            data = self.kubo.cat(cid)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        except (OSError, ValueError) as exc:
            raise ContentError(str(exc)) from exc
        except Exception as exc:
            raise ContentError(f"Unable to retrieve {cid}: {exc}") from exc
        return target

    def pin(self, cid: str) -> None:
        try:
            self.kubo.pin_add(cid)
        except Exception as exc:
            raise ContentError(f"Unable to pin {cid}: {exc}") from exc

    def unpin(self, cid: str) -> None:
        try:
            self.kubo.pin_remove(cid)
        except Exception as exc:
            raise ContentError(f"Unable to unpin {cid}: {exc}") from exc

    def pins(self) -> dict[str, dict[str, str]]:
        try:
            return self.kubo.pin_list()
        except Exception as exc:
            raise ContentError(f"Unable to list pins: {exc}") from exc
