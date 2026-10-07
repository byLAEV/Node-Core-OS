"""Node Core OS configuration and filesystem layout."""

from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path

DEFAULT_DATA_DIR = Path.home() / ".node-core"

@dataclass
class NodeConfig:
    data_dir: Path = DEFAULT_DATA_DIR
    local_storage_path: Path = DEFAULT_DATA_DIR / "storage"
    ipfs_repo_path: Path = DEFAULT_DATA_DIR / "ipfs"
    ipfs_api: str = "http://127.0.0.1:5001"
    ipfs_gateway: str = "http://127.0.0.1:8080"
    ipfs_executable: str = "ipfs"
    ipfs_profile: str = "unixfs-v1-2025"
    age_executable: str = "age"

    @property
    def config_path(self) -> Path:
        return self.data_dir / "config.json"

    @property
    def backup_path(self) -> Path:
        return self.data_dir / "backups"

    @property
    def secrets_path(self) -> Path:
        return self.data_dir / "secrets"

    @property
    def backup_history_path(self) -> Path:
        return self.backup_path / "history.json"

    @classmethod
    def load(cls) -> "NodeConfig":
        path = Path(os.environ.get("NODE_CORE_CONFIG", str(DEFAULT_DATA_DIR / "config.json")))
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        defaults = cls()
        return cls(
            data_dir=Path(data.get("data_dir", defaults.data_dir)),
            local_storage_path=Path(data.get("local_storage_path", defaults.local_storage_path)),
            ipfs_repo_path=Path(data.get("ipfs_repo_path", defaults.ipfs_repo_path)),
            ipfs_api=data.get("ipfs_api", defaults.ipfs_api),
            ipfs_gateway=data.get("ipfs_gateway", defaults.ipfs_gateway),
            ipfs_executable=data.get("ipfs_executable", defaults.ipfs_executable),
            ipfs_profile=data.get("ipfs_profile", defaults.ipfs_profile),
            age_executable=data.get("age_executable", defaults.age_executable),
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
        self.ipfs_repo_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_path.mkdir(parents=True, exist_ok=True)
        self.secrets_path.mkdir(parents=True, exist_ok=True)
        self.backup_path.chmod(0o700)
        self.secrets_path.chmod(0o700)

    def save(self) -> None:
        self.ensure_directories()
        payload = {key: str(value) for key, value in asdict(self).items()}
        self.config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self.config_path.chmod(0o600)
