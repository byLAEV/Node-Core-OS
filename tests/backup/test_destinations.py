from pathlib import Path
import tempfile
import unittest

from node_core.backup.destinations import FileDestination
from node_core.backup.pinata import PinataClient


class FileDestinationTests(unittest.TestCase):
    def test_pinata_rejects_non_ncb_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            credential = root / "pinata.jwt"
            credential.write_text("test-jwt\n", encoding="utf-8")
            source = root / "plaintext.tar"
            source.write_bytes(b"plaintext")
            with self.assertRaises(ValueError):
                PinataClient(credential).upload_file(source)

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
