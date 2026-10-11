"""Tests for HashPaper's local transparent document foundation."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hashpaper.documents import build_transparent_package, sha256_bytes, write_original, write_package


class HashPaperDocumentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_sha256_uses_exact_bytes(self):
        data = "á\nline two\n".encode("utf-8")
        self.assertEqual(sha256_bytes(data), hashlib.sha256(data).hexdigest())

    def test_original_is_never_overwritten(self):
        path = self.root / "document-001.md"
        result = write_original(path, "Original text")
        self.assertEqual(path.read_bytes(), b"Original text")
        self.assertEqual(result["sha256"], hashlib.sha256(b"Original text").hexdigest())
        with self.assertRaises(FileExistsError):
            write_original(path, "Replacement text")
        self.assertEqual(path.read_bytes(), b"Original text")

    def test_package_includes_full_original_and_transparent_identity(self):
        original = self.root / "document.md"
        original.write_text("# Original\n\nFull body, not just a hash.\n", encoding="utf-8")
        profile = {
            "identity_id": "synthetic-id",
            "full_name": "Synthetic Test Person",
            "document_number": "TEST-0001",
            "identity_status": "declared",
            "node_id": "peer-synthetic",
        }
        package = build_transparent_package(original_path=original, identity_profile=profile, node_id="peer-synthetic")
        self.assertEqual(package["document"]["original_text"], original.read_text(encoding="utf-8"))
        self.assertEqual(package["document"]["sha256"], hashlib.sha256(original.read_bytes()).hexdigest())
        self.assertEqual(package["identity"]["fields"]["full_name"], "Synthetic Test Person")
        self.assertFalse(package["encryption"]["implemented"])
        self.assertEqual(package["opentimestamps"]["status"], "NOT_SUBMITTED")
        self.assertIsNone(package["bitcoin"]["block_hash"])
        self.assertIsNone(package["publication"]["ipfs_cid"])

    def test_package_rejects_non_utf8_source(self):
        original = self.root / "binary.txt"
        original.write_bytes(bytes([255, 254, 253]))
        with self.assertRaises(ValueError):
            build_transparent_package(original_path=original, identity_profile=None, node_id=None)

    def test_package_writes_valid_json_with_private_permissions(self):
        original = self.root / "doc.txt"
        original.write_text("test", encoding="utf-8")
        output = self.root / "package.json"
        package = build_transparent_package(original_path=original, identity_profile=None, node_id=None)
        write_package(output, package)
        saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(saved["document"]["original_text"], "test")
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
