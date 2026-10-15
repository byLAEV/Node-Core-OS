import json
import os
from pathlib import Path
import tempfile
import unittest

from node_core.identity.node_identity import NodeIdentityError, NodeIdentityStore


class NodeIdentityStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.store = NodeIdentityStore(self.root)

    def test_initialization_creates_persistent_ed25519_identity(self):
        metadata = self.store.initialize()
        self.assertEqual(metadata["schema_version"], 1)
        self.assertEqual(metadata["algorithm"], "Ed25519")
        self.assertTrue(metadata["node_id"].startswith("sha256:"))
        self.assertEqual(len(metadata["public_key"]), 64)
        self.assertTrue(self.store.private_key_path.is_file())
        self.assertEqual(self.store.load(), metadata)

    def test_initialization_is_idempotent(self):
        first = self.store.initialize()
        original_key = self.store.private_key_path.read_bytes()
        second = self.store.initialize()
        self.assertEqual(first, second)
        self.assertEqual(self.store.private_key_path.read_bytes(), original_key)

    def test_independent_data_directories_get_different_identities(self):
        first = self.store.initialize()
        other = NodeIdentityStore(self.root / "other").initialize()
        self.assertNotEqual(first["node_id"], other["node_id"])
        self.assertNotEqual(first["public_key"], other["public_key"])

    def test_missing_private_key_fails_closed_without_regeneration(self):
        original = self.store.initialize()
        self.store.private_key_path.unlink()
        with self.assertRaises(NodeIdentityError):
            self.store.initialize()
        self.assertFalse(self.store.private_key_path.exists())
        self.assertEqual(json.loads(self.store.metadata_path.read_text())["node_id"],
                         original["node_id"])

    def test_missing_metadata_fails_closed(self):
        self.store.initialize()
        self.store.metadata_path.unlink()
        with self.assertRaises(NodeIdentityError):
            self.store.initialize()
        self.assertTrue(self.store.private_key_path.exists())
        self.assertFalse(self.store.metadata_path.exists())

    def test_corrupt_metadata_is_rejected(self):
        self.store.initialize()
        self.store.metadata_path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(NodeIdentityError):
            self.store.load()

    def test_public_key_mismatch_is_rejected(self):
        metadata = self.store.initialize()
        metadata["public_key"] = "00" * 32
        self.store.metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        with self.assertRaises(NodeIdentityError):
            self.store.load()

    def test_sign_and_verify(self):
        metadata = self.store.initialize()
        message = b"Node Core OS identity proof test"
        signature = self.store.sign(message)
        self.assertTrue(NodeIdentityStore.verify(metadata["public_key"], message, signature))
        self.assertFalse(NodeIdentityStore.verify(
            metadata["public_key"], b"different message", signature
        ))

    def test_invalid_public_key_or_signature_returns_false(self):
        self.assertFalse(NodeIdentityStore.verify("not-hex", b"message", b"signature"))
        self.assertFalse(NodeIdentityStore.verify("00" * 32, b"message", b"invalid"))

    @unittest.skipUnless(os.name == "posix", "POSIX file permissions required")
    def test_private_key_file_has_restrictive_permissions(self):
        self.store.initialize()
        self.assertEqual(self.store.private_key_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.store.private_dir.stat().st_mode & 0o777, 0o700)


if __name__ == "__main__":
    unittest.main()
