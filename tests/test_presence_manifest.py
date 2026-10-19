"""Tests for unanimous signed presence manifests."""
import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.presence_manifest import (
    PresenceManifestError,
    create_manifest_body,
    sign_manifest,
    verify_manifest,
)


class PresenceManifestTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.identities = [
            NodeIdentityStore(root / "node-a"),
            NodeIdentityStore(root / "node-b"),
        ]
        self.metadata = [identity.initialize() for identity in self.identities]

    def tearDown(self):
        self.tempdir.cleanup()

    def body(self):
        return create_manifest_body([
            {"node_id": item["node_id"], "public_key": item["public_key"]}
            for item in self.metadata
        ], epoch=100, created_at=100)

    def test_all_roster_members_must_sign(self):
        body = self.body()
        signatures = [sign_manifest(self.identities[0], body)]
        with self.assertRaisesRegex(PresenceManifestError, "not unanimous"):
            verify_manifest(body, signatures)

    def test_unanimous_manifest_verifies(self):
        body = self.body()
        signatures = [sign_manifest(identity, body) for identity in self.identities]
        result = verify_manifest(body, signatures)
        self.assertTrue(result["unanimous"])
        self.assertEqual(result["node_count"], 2)
        self.assertEqual(len(result["manifest_sha256"]), 64)

    def test_signature_cannot_be_reused_for_changed_roster(self):
        body = self.body()
        signatures = [sign_manifest(identity, body) for identity in self.identities]
        changed = dict(body)
        changed["epoch"] = 101
        with self.assertRaises(PresenceManifestError):
            verify_manifest(changed, signatures)

    def test_duplicate_signer_is_rejected(self):
        body = self.body()
        signature = sign_manifest(self.identities[0], body)
        with self.assertRaisesRegex(PresenceManifestError, "duplicate"):
            verify_manifest(body, [signature, signature])

    def test_signer_must_be_in_roster(self):
        body = create_manifest_body([
            {"node_id": self.metadata[0]["node_id"],
             "public_key": self.metadata[0]["public_key"]}
        ], epoch=100, created_at=100)
        with self.assertRaisesRegex(PresenceManifestError, "not present"):
            sign_manifest(self.identities[1], body)


if __name__ == "__main__":
    unittest.main()
