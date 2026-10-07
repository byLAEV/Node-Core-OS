"""Kubo identity and key export for V1 backups."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class KuboIdentity:
    peer_id: str | None
    version: str | None


class KuboBackupSource:
    def __init__(self, executable: str = "ipfs", repo_path: Path | None = None) -> None:
        self.executable = executable
        self.repo_path = repo_path

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        if self.repo_path is not None:
            env["IPFS_PATH"] = str(self.repo_path.resolve())
        return env

    def identity(self) -> KuboIdentity:
        env = self._env()
        result = subprocess.run([self.executable, "id"], check=True, capture_output=True, text=True, env=env)
        payload = json.loads(result.stdout)
        version_result = subprocess.run([self.executable, "version"], check=True, capture_output=True, text=True, env=env)
        fields = version_result.stdout.strip().split()
        return KuboIdentity(payload.get("ID"), fields[-1] if fields else None)

    def export_identity(self, destination: Path) -> Path:
        config_path = (self.repo_path / "config") if self.repo_path else Path.home() / ".ipfs" / "config"
        env_repo = os.environ.get("IPFS_PATH")
        if env_repo and self.repo_path is None:
            config_path = Path(env_repo) / "config"
        if not config_path.is_file():
            raise FileNotFoundError(f"Kubo config not found: {config_path}")
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        identity = payload.get("Identity")
        if not isinstance(identity, dict) or not identity.get("PeerID") or not identity.get("PrivKey"):
            raise RuntimeError("Kubo identity is missing from config.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        destination.chmod(0o600)
        return destination

    def list_keys(self) -> list[str]:
        result = subprocess.run(
            [self.executable, "key", "ls"],
            check=True,
            capture_output=True,
            text=True,
            env=self._env(),
        )
        return [line.split()[0] for line in result.stdout.splitlines() if line.split()]

    def export_key(self, name: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [self.executable, "key", "export", name, "--output", str(destination)],
            check=True,
            capture_output=True,
            text=True,
            env=self._env(),
        )
        destination.chmod(0o600)
        return destination
