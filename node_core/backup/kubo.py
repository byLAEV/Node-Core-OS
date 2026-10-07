"""Kubo identity and key export for V1 backups."""

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class KuboIdentity:
    peer_id: str | None
    version: str | None


class KuboBackupSource:
    def __init__(self, executable: str = "ipfs") -> None:
        self.executable = executable

    def identity(self) -> KuboIdentity:
        result = subprocess.run([self.executable, "id"], check=True, capture_output=True, text=True)
        payload = json.loads(result.stdout)
        version_result = subprocess.run([self.executable, "version"], check=True, capture_output=True, text=True)
        fields = version_result.stdout.strip().split()
        return KuboIdentity(payload.get("ID"), fields[-1] if fields else None)

    def list_keys(self) -> list[str]:
        result = subprocess.run([self.executable, "key", "ls"], check=True, capture_output=True, text=True)
        return [line.split()[0] for line in result.stdout.splitlines() if line.split()]

    def export_key(self, name: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [self.executable, "key", "export", name, "--output", str(destination)],
            check=True,
            capture_output=True,
            text=True,
        )
        destination.chmod(0o600)
        return destination
