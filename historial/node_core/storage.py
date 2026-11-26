"""Local storage abstraction and BIOS-managed storage state."""

from pathlib import Path
from typing import BinaryIO


class StorageManager:
    """Own the local storage root and its isolated private/shared namespaces."""

    PRIVATE_DIRECTORY = "private"
    SHARED_DIRECTORY = "shared"

    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser()

    @property
    def private_path(self) -> Path:
        """Return the private local storage directory."""
        return self.path(self.PRIVATE_DIRECTORY)

    @property
    def shared_path(self) -> Path:
        """Return the local directory reserved for node synchronization."""
        return self.path(self.SHARED_DIRECTORY)

    def initialize(self) -> None:
        """Create the storage root and both local storage areas."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.private_path.mkdir(parents=True, exist_ok=True)
        self.shared_path.mkdir(parents=True, exist_ok=True)

    def path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        root = self.root.resolve()
        if root not in candidate.parents and candidate != root:
            raise ValueError("Storage path escapes the Node storage root.")
        return candidate

    def exists(self, relative: str) -> bool:
        return self.path(relative).exists()

    def open(self, relative: str, mode: str = "rb") -> BinaryIO:
        target = self.path(relative)
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            target.parent.mkdir(parents=True, exist_ok=True)
        return target.open(mode)

    def write_bytes(self, relative: str, data: bytes) -> Path:
        target = self.path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    def read_bytes(self, relative: str) -> bytes:
        return self.path(relative).read_bytes()

    def delete(self, relative: str) -> None:
        target = self.path(relative)
        if target.is_dir():
            raise IsADirectoryError(relative)
        target.unlink()
