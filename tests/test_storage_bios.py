import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from node_core.storage import StorageManager
from node_core.ui import MainMenu


class StorageBiosTests(unittest.TestCase):
    def test_initialize_creates_private_and_shared_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(Path(temp_dir) / "storage")

            storage.initialize()

            self.assertTrue(storage.root.is_dir())
            self.assertTrue(storage.private_path.is_dir())
            self.assertTrue(storage.shared_path.is_dir())
            self.assertNotEqual(storage.private_path, storage.shared_path)

    def test_private_and_shared_files_are_separate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(Path(temp_dir) / "storage")
            storage.initialize()

            storage.write_bytes("private/private.txt", b"private")
            storage.write_bytes("shared/shared.txt", b"shared")

            self.assertEqual(storage.read_bytes("private/private.txt"), b"private")
            self.assertEqual(storage.read_bytes("shared/shared.txt"), b"shared")
            self.assertFalse((storage.private_path / "shared.txt").exists())
            self.assertFalse((storage.shared_path / "private.txt").exists())

    def test_storage_bios_shows_two_areas_and_returns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(Path(temp_dir) / "storage")
            runtime = SimpleNamespace(
                storage=storage,
                config=SimpleNamespace(local_storage_path=storage.root),
            )
            menu = MainMenu(runtime)
            with patch("builtins.input", side_effect=["0"]), patch("builtins.print") as output:
                menu.storage_bios()

            printed = "\n".join(str(call.args[0]) for call in output.call_args_list if call.args)
            self.assertIn("Enter Private Local Storage", printed)
            self.assertIn("Enter Shared Node Storage", printed)
            self.assertTrue(storage.private_path.is_dir())
            self.assertTrue(storage.shared_path.is_dir())

    def test_private_and_shared_navigation_reports_contents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = StorageManager(Path(temp_dir) / "storage")
            storage.initialize()
            (storage.private_path / "notes.txt").write_text("private", encoding="utf-8")
            (storage.shared_path / "manifest.json").write_text("{}", encoding="utf-8")

            with patch("builtins.input", return_value=""), patch("builtins.print") as output:
                MainMenu._browse_storage_area("Private Local Storage", storage.private_path)
                MainMenu._browse_storage_area("Shared Node Storage", storage.shared_path)

            printed = "\n".join(str(call.args[0]) for call in output.call_args_list if call.args)
            self.assertIn("notes.txt", printed)
            self.assertIn("manifest.json", printed)
            self.assertIn("Access: OK", printed)


if __name__ == "__main__":
    unittest.main()
