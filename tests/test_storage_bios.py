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
            runtime = SimpleNamespace(storage=storage, config=SimpleNamespace(local_storage_path=storage.root))
            menu = MainMenu(runtime)
            with patch("builtins.input", side_effect=["0"]), patch("builtins.print") as output:
                menu.storage_bios()
            printed = "\n".join(str(call.args[0]) for call in output.call_args_list if call.args)
            self.assertIn("Enter Private Local Storage", printed)
            self.assertIn("Enter Shared Node Storage", printed)
            self.assertTrue(storage.private_path.is_dir())
            self.assertTrue(storage.shared_path.is_dir())

    def test_create_text_file_supports_multiline_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            inputs = ["notes", "first line", "second line", ":SAVE", ""]
            with patch("builtins.input", side_effect=inputs), patch("builtins.print"):
                MainMenu._create_text_file(None, path)
            self.assertEqual((path / "notes.txt").read_text(encoding="utf-8"), "first line\nsecond line\n")

    def test_create_text_file_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            target = path / "notes.txt"
            target.write_text("original", encoding="utf-8")
            with patch("builtins.input", side_effect=["notes", ""]), patch("builtins.print"):
                MainMenu._create_text_file(None, path)
            self.assertEqual(target.read_text(encoding="utf-8"), "original")

    def test_browse_storage_area_shows_ten_files_per_page(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            for index in range(12):
                (path / f"file-{index:02}.txt").write_text(str(index), encoding="utf-8")
            with patch("builtins.input", side_effect=["1", "0"]), patch("builtins.print") as output:
                MainMenu._browse_storage_area("Private Local Storage", path)
            printed = "\n".join(str(call.args[0]) for call in output.call_args_list if call.args)
            self.assertIn("Page 1/2", printed)
            self.assertIn("Page 2/2", printed)
            self.assertIn("file-09.txt", printed)
            self.assertIn("file-10.txt", printed)


if __name__ == "__main__":
    unittest.main()
