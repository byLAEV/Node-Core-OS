"""Tests for private SHA-256 persistence manifests."""

from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

from node_core.persistence_integrity import (
    PersistenceIntegrityError,
    capture_persistence_manifest,
    compare_persistence_manifests,
    write_persistence_manifest,
)


class PersistenceIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="node-core-integrity-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data = self.root / "node-data"
        identity = self.data / "identity"
        (identity / "private").mkdir(parents=True)
        (identity / "node.json").write_text(
            '{"schema_version":1,"algorithm":"Ed25519","node_id":"sha256:test"}\n',
            encoding="utf-8",
        )
        (identity / "private" / "node.key").write_text(
            "SYNTHETIC PRIVATE KEY FIXTURE\n", encoding="utf-8"
        )
        (identity / "profile.json").write_text(
            '{"schema_version":1,"identity_id":"synthetic-profile"}\n',
            encoding="utf-8",
        )
        (identity / "entity-registry.json").write_text(
            '{"schema_version":1,"entities":[]}\n', encoding="utf-8"
        )

        self.storage = self.data / "storage"
        self.storage.mkdir(parents=True)
        (self.storage / "document.txt").write_text("local persistent data\n", encoding="utf-8")

        self.kubo = self.data / "ipfs"
        (self.kubo / "blocks").mkdir(parents=True)
        (self.kubo / "config").write_text('{"Identity":{"PeerID":"synthetic"}}\n', encoding="utf-8")
        (self.kubo / "blocks" / "fixture-block").write_bytes(b"synthetic-ipfs-block")
        # These Kubo runtime paths are intentionally excluded from persistence
        # comparisons because their contents can change when a daemon starts.
        (self.kubo / "api").write_text("/ip4/127.0.0.1/tcp/5001\n", encoding="utf-8")
        (self.kubo / "repo.lock").write_text("volatile lock\n", encoding="utf-8")
        (self.kubo / "datastore").mkdir()
        (self.kubo / "datastore" / "LOCK").write_text("volatile lock\n", encoding="utf-8")

    def capture(self) -> dict:
        return capture_persistence_manifest(self.data)

    def test_manifest_covers_all_required_persistence_scopes(self) -> None:
        manifest = self.capture()
        self.assertEqual(
            set(manifest["scopes"]),
            {"node_identity", "profile", "entity_registry", "local_storage", "kubo_ipfs"},
        )
        identity_files = {
            item["path"] for item in manifest["scopes"]["node_identity"]["files"]
        }
        self.assertIn("private/node.key", identity_files)
        self.assertIn("node.json", identity_files)
        kubo_files = {
            item["path"] for item in manifest["scopes"]["kubo_ipfs"]["files"]
        }
        self.assertIn("config", kubo_files)
        self.assertIn("blocks/fixture-block", kubo_files)
        self.assertNotIn("api", kubo_files)
        self.assertNotIn("repo.lock", kubo_files)
        self.assertNotIn("datastore/LOCK", kubo_files)

    def test_unchanged_state_matches_exactly(self) -> None:
        before = self.capture()
        after = self.capture()
        self.assertTrue(compare_persistence_manifests(before, after)["matches"])

    def test_added_removed_and_changed_files_are_detected(self) -> None:
        before = self.capture()
        (self.storage / "document.txt").write_text("updated local data\n", encoding="utf-8")
        (self.storage / "new.txt").write_text("new file\n", encoding="utf-8")
        (self.kubo / "blocks" / "fixture-block").unlink()
        after = self.capture()

        result = compare_persistence_manifests(before, after)
        self.assertFalse(result["matches"])
        self.assertIn("local_storage/document.txt", result["changed"])
        self.assertIn("local_storage/new.txt", result["added"])
        self.assertIn("kubo_ipfs/blocks/fixture-block", result["removed"])

    def test_symlinks_are_hashed_without_following_them(self) -> None:
        secret = self.root / "outside-secret.txt"
        secret.write_text("must not be read\n", encoding="utf-8")
        link = self.storage / "outside-link"
        try:
            link.symlink_to(secret)
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are unavailable on this test platform.")

        manifest = self.capture()
        record = next(
            item
            for item in manifest["scopes"]["local_storage"]["files"]
            if item["path"] == "outside-link"
        )
        self.assertEqual(record["kind"], "symlink")
        self.assertNotEqual(record["sha256"], __import__("hashlib").sha256(secret.read_bytes()).hexdigest())

    def test_private_manifest_is_written_with_owner_only_permissions(self) -> None:
        output = self.root / "private" / "before.json"
        write_persistence_manifest(output, self.capture())
        mode = stat.S_IMODE(output.stat().st_mode)
        self.assertEqual(mode, 0o600)

    def test_missing_profile_fails_closed(self) -> None:
        (self.data / "identity" / "profile.json").unlink()
        with self.assertRaises(PersistenceIntegrityError):
            self.capture()

    def test_symlink_data_root_is_rejected(self) -> None:
        alias = self.root / "node-data-alias"
        try:
            alias.symlink_to(self.data, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are unavailable on this test platform.")
        with self.assertRaises(PersistenceIntegrityError):
            capture_persistence_manifest(alias)


if __name__ == "__main__":
    unittest.main()
