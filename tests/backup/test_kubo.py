import json
from pathlib import Path
import tempfile
import unittest

from node_core.backup.kubo import KuboBackupSource


class KuboBackupSourceTests(unittest.TestCase):
    def test_export_identity_reads_config_and_restricts_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "ipfs"
            repo.mkdir()
            (repo / "config").write_text(
                json.dumps({
                    "Identity": {
                        "PeerID": "12D3KooW-test",
                        "PrivKey": "private-key-material",
                    }
                }),
                encoding="utf-8",
            )
            destination = root / "payload" / "identity" / "kubo-identity.json"
            source = KuboBackupSource(repo_path=repo)
            source.export_identity(destination)

            payload = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(payload["PeerID"], "12D3KooW-test")
            self.assertEqual(payload["PrivKey"], "private-key-material")
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
