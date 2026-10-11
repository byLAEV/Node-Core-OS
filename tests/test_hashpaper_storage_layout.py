"""Tests for persistent HashPaper data directories in Node Core OS config."""

from pathlib import Path
import tempfile
import unittest

from node_core.config import NodeConfig


class HashPaperStorageLayoutTests(unittest.TestCase):
    def test_hashpaper_data_is_outside_application_code_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data_dir = root / ".node-core"
            config = NodeConfig(
                data_dir=data_dir,
                local_storage_path=data_dir / "storage",
                ipfs_repo_path=data_dir / "ipfs",
            )
            config.ensure_directories()
            expected = ["documents", "proofs", "packages", "records"]
            for name in expected:
                path = data_dir / "hashpaper" / name
                self.assertTrue(path.is_dir(), str(path))
                self.assertFalse((data_dir / "app" / "hashpaper" / name).exists())


if __name__ == "__main__":
    unittest.main()
