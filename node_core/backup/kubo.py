"""Kubo identity and key inspection for V1 backups."""

from dataclasses import dataclass
import json
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
        result = subprocess.run([self.executable, "key", "list"], check=True, capture_output=True, text=True)
        return [line.split()[0] for line in result.stdout.splitlines() if line.split()]
