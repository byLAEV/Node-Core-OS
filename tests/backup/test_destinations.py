from pathlib import Path
import tempfile
import unittest

from node_core.backup.destinations import FileDestination


class FileDestinationTests(unittest.TestCase):
    def test_file_destination_sets_private_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.ncb"
            destination = root / "out" / "backup.ncb"
            source.write_bytes(b"encrypted")
            FileDestination().save(source, destination)
            self.assertEqual(destination.read_bytes(), b"encrypted")
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
