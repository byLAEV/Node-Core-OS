"""Local storage abstraction and BIOS-managed storage state."""

from pathlib import Path
from typing import BinaryIO

class StorageManager:
    def __init__(self, root: Path) -> None:
        self.root = root

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

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
