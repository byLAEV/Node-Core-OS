"""Node Core OS configuration and filesystem layout."""

from dataclasses import dataclass
import json
import os
from pathlib import Path


@dataclass
class NodeConfig:
    data_dir: Path = Path.home() / ".node-core"
    local_storage_path: Path = Path.home() / ".node-core" / "storage"
    ipfs_api: str = "http://127.0.0.1:5001"

    @classmethod
    def load(cls) -> "NodeConfig":
        path = Path(os.environ.get("NODE_CORE_CONFIG", str(Path.home() / ".node-core" / "config.json")))
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            data_dir=Path(data.get("data_dir", cls.data_dir)),
            local_storage_path=Path(data.get("local_storage_path", cls.local_storage_path)),
            ipfs_api=data.get("ipfs_api", cls.ipfs_api),
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
