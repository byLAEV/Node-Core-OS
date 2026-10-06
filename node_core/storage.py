"""Local storage abstraction."""

from pathlib import Path
from typing import BinaryIO


class StorageManager:
    def __init__(self, root: Path) -> None:
        self.root = root

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if self.root.resolve() not in candidate.parents and candidate != self.root.resolve():
            raise ValueError("Storage path escapes the Node storage root.")
        return candidate

    def open(self, relative: str, mode: str = "rb") -> BinaryIO:
        return self.path(relative).open(mode)
