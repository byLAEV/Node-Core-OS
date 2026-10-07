from pathlib import Path
import tarfile
import tempfile
import unittest

from node_core.backup.manager import BackupManager
from node_core.config import NodeConfig


class FakeKubo:
    def identity(self):
        return type("Identity", (), {"peer_id": "12D3KooW-test", "version": "0.43.1"})()

    def list_keys(self):
        return ["self"]

    def export_identity(self, destination: Path):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            '{"PeerID":"12D3KooW-test","PrivKey":"secret"}\n',
            encoding="utf-8",
        )
        destination.chmod(0o600)
        return destination

    def export_key(self, name: str, destination: Path):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"key-material")
        destination.chmod(0o600)
        return destination


class FakeEncryption:
    def available(self):
        return True

    def encrypt_with_passphrase(self, source: Path, destination: Path, passphrase: str):
        destination.write_bytes(source.read_bytes())
        destination.chmod(0o600)


class BackupPackagingTests(unittest.TestCase):
    def test_create_backup_packages_identity_and_keys_before_encryption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = NodeConfig(data_dir=root / "node")
            manager = BackupManager(config)
            manager.kubo = FakeKubo()
            manager.encryption = FakeEncryption()

            target = manager.create_backup("test-passphrase")

            self.assertEqual(list(config.backup_path.glob("node-core-backup-*")), [])
            with tarfile.open(target, "r:") as archive:
                members = archive.getnames()
                self.assertIn("manifest.json", members)
                self.assertIn("identity/kubo-identity.json", members)
                self.assertIn("keys/self.key", members)


if __name__ == "__main__":
    unittest.main()
