"""Backup destination abstractions."""

from pathlib import Path
import shutil


class FileDestination:
    def save(self, source: Path, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        destination.chmod(0o600)
        return destination
