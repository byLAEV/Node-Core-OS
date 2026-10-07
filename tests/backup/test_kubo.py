import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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

    @patch("node_core.backup.kubo.subprocess.run")
    def test_ipfs_commands_are_bound_to_configured_repo(self, run):
        run.side_effect = [
            type("Result", (), {"stdout": '{"ID":"12D3KooW-test"}'})(),
            type("Result", (), {"stdout": "ipfs version 0.43.1"})(),
            type("Result", (), {"stdout": "self self"})(),
        ]
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "ipfs"
            repo.mkdir()
            source = KuboBackupSource(executable="/node/bin/ipfs", repo_path=repo)

            source.identity()
            source.list_keys()

            self.assertEqual(run.call_count, 3)
            for call in run.call_args_list:
                self.assertEqual(call.kwargs["env"]["IPFS_PATH"], str(repo.resolve()))


if __name__ == "__main__":
    unittest.main()
