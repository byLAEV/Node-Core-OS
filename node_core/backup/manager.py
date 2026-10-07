"""Backup orchestration foundation for V1."""

from node_core.backup.encryption import AgeEncryption
from node_core.backup.kubo import KuboBackupSource
from node_core.backup.manifest import create_manifest, serialize_manifest
from node_core.config import NodeConfig


class BackupManager:
    def __init__(self, config: NodeConfig) -> None:
        self.config = config
        self.kubo = KuboBackupSource(config.ipfs_executable)
        self.encryption = AgeEncryption(config.age_executable)

    def status(self) -> dict[str, object]:
        identity = self.kubo.identity()
        return {
            "age_available": self.encryption.available(),
            "peer_id": identity.peer_id,
            "kubo_version": identity.version,
            "backup_dir": str(self.config.backup_path),
        }

    def inspect(self) -> dict[str, object]:
        identity = self.kubo.identity()
        keys = self.kubo.list_keys()
        return {
            "manifest": serialize_manifest(
                create_manifest(
                    kubo_version=identity.version,
                    peer_id=identity.peer_id,
                    keys=keys,
                )
            ).decode("utf-8"),
            "keys": keys,
        }
