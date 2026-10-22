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
    auto_start_kubo: bool = True

    @property
    def config_path(self) -> Path:
        return self.data_dir / "config.json"

    @classmethod
    def load(cls) -> "NodeConfig":
        configured_data_dir = Path(
            os.environ.get("NODE_CORE_DATA_DIR", str(DEFAULT_DATA_DIR))
        ).expanduser()
        path = Path(
            os.environ.get("NODE_CORE_CONFIG", str(configured_data_dir / "config.json"))
        ).expanduser()
        defaults = cls(
            data_dir=configured_data_dir,
            local_storage_path=configured_data_dir / "storage",
            ipfs_repo_path=configured_data_dir / "ipfs",
        )
        if not path.exists():
            return defaults
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            data_dir=Path(data.get("data_dir", defaults.data_dir)).expanduser(),
            local_storage_path=Path(data.get("local_storage_path", defaults.local_storage_path)).expanduser(),
            ipfs_repo_path=Path(data.get("ipfs_repo_path", defaults.ipfs_repo_path)).expanduser(),
            ipfs_api=data.get("ipfs_api", defaults.ipfs_api),
            ipfs_gateway=data.get("ipfs_gateway", defaults.ipfs_gateway),
            ipfs_executable=data.get("ipfs_executable", defaults.ipfs_executable),
            ipfs_profile=data.get("ipfs_profile", defaults.ipfs_profile),
            auto_start_kubo=bool(data.get("auto_start_kubo", defaults.auto_start_kubo)),
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
        self.ipfs_repo_path.parent.mkdir(parents=True, exist_ok=True)
        # HashPaper keeps its own application data, but Kubo's repository and
        # daemon remain exclusively managed by Node Core OS at ipfs_repo_path.
        hashpaper_root = self.data_dir / "hashpaper"
        for name in ("documents", "ipfs", "packages", "records"):
            (hashpaper_root / name).mkdir(parents=True, exist_ok=True)
        # New HashPaper originals and their adjacent .ots proofs live in the
        # Node Core OS local-storage namespace. Existing hashpaper/documents
        # files remain supported by HashPaper's history reader.
        (self.local_storage_path / "opentimestamps").mkdir(parents=True, exist_ok=True)

    def save(self) -> None:
        self.ensure_directories()
        payload = {
            key: str(value) if isinstance(value, Path) else value
            for key, value in asdict(self).items()
        }
        self.config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
