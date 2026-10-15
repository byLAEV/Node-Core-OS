import json
import os
from pathlib import Path
import tempfile
import unittest

from node_core.identity.associations import (
    IdentityAssociationError,
    IdentityAssociationStore,
)
from node_core.identity.node_identity import NodeIdentityStore
from node_core.identity.profile import IdentityProfileStore


class IdentityAssociationStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.profile = IdentityProfileStore(self.root)
        self.profile.save_declared_profile(
            full_name="Synthetic Test Person",
            issuing_country="Costa Rica",
            document_type="Synthetic test document",
            document_number="TEST-ONLY-0001",
        )
        self.node = NodeIdentityStore(self.root / "node-a")
        self.metadata = self.node.initialize()
        self.associations = IdentityAssociationStore(self.root)

    def issue_signed_proof(self):
        challenge = self.associations.issue_challenge(self.profile, self.metadata)
        message = bytes.fromhex(challenge["message_hex"])
        signature = self.node.sign(message).hex()
        return challenge, signature

    def test_valid_proof_records_control_verified_association(self):
        challenge, signature = self.issue_signed_proof()
        record = self.associations.complete_association(
            self.profile, challenge["challenge_id"], signature
        )
        self.assertEqual(record["status"], "control_verified")
        self.assertEqual(record["node_id"], self.metadata["node_id"])
        self.assertEqual(record["profile_identity_id"], self.profile.load()["identity_id"])
        self.assertEqual(len(self.associations.list_associations()), 1)

    def test_invalid_signature_does_not_consume_challenge(self):
        challenge = self.associations.issue_challenge(self.profile, self.metadata)
        with self.assertRaises(IdentityAssociationError):
            self.associations.complete_association(
                self.profile, challenge["challenge_id"], "00" * 64
            )
        signature = self.node.sign(bytes.fromhex(challenge["message_hex"])).hex()
        record = self.associations.complete_association(
            self.profile, challenge["challenge_id"], signature
        )
        self.assertEqual(record["status"], "control_verified")

    def test_challenge_cannot_be_replayed(self):
        challenge, signature = self.issue_signed_proof()
        self.associations.complete_association(
            self.profile, challenge["challenge_id"], signature
        )
        with self.assertRaises(IdentityAssociationError):
            self.associations.complete_association(
                self.profile, challenge["challenge_id"], signature
            )

    def test_multiple_nodes_can_be_associated_with_one_profile(self):
        challenge_a, signature_a = self.issue_signed_proof()
        self.associations.complete_association(
            self.profile, challenge_a["challenge_id"], signature_a
        )
        node_b = NodeIdentityStore(self.root / "node-b")
        metadata_b = node_b.initialize()
        challenge_b = self.associations.issue_challenge(self.profile, metadata_b)
        signature_b = node_b.sign(bytes.fromhex(challenge_b["message_hex"])).hex()
        self.associations.complete_association(
            self.profile, challenge_b["challenge_id"], signature_b
        )
        records = self.associations.list_associations(self.profile.load()["identity_id"])
        self.assertEqual(len(records), 2)
        self.assertNotEqual(records[0]["node_id"], records[1]["node_id"])
        self.assertIsNone(self.profile.load()["node_id"])

    def test_wrong_node_cannot_sign_another_nodes_challenge(self):
        challenge = self.associations.issue_challenge(self.profile, self.metadata)
        other_node = NodeIdentityStore(self.root / "other-node")
        other_node.initialize()
        wrong_signature = other_node.sign(bytes.fromhex(challenge["message_hex"])).hex()
        with self.assertRaises(IdentityAssociationError):
            self.associations.complete_association(
                self.profile, challenge["challenge_id"], wrong_signature
            )

    def test_profile_must_exist(self):
        empty_profile = IdentityProfileStore(self.root / "empty")
        with self.assertRaises(IdentityAssociationError):
            self.associations.issue_challenge(empty_profile, self.metadata)

    def test_node_id_must_match_public_key(self):
        tampered = dict(self.metadata)
        tampered["node_id"] = "sha256:" + "0" * 64
        with self.assertRaises(IdentityAssociationError):
            self.associations.issue_challenge(self.profile, tampered)

    def test_revocation_keeps_audit_record(self):
        challenge, signature = self.issue_signed_proof()
        record = self.associations.complete_association(
            self.profile, challenge["challenge_id"], signature
        )
        revoked = self.associations.revoke(record["association_id"])
        self.assertEqual(revoked["status"], "revoked")
        self.assertIsNotNone(revoked["revoked_at"])
        self.assertEqual(len(self.associations.list_associations()), 1)

    def test_unknown_association_cannot_be_revoked(self):
        with self.assertRaises(IdentityAssociationError):
            self.associations.revoke("not-an-association")

    def test_association_store_permissions_are_restrictive_on_posix(self):
        self.issue_signed_proof()
        if os.name == "posix":
            self.assertEqual(self.associations.path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.associations.identity_dir.stat().st_mode & 0o777, 0o700)

    def test_corrupt_association_store_fails_closed(self):
        self.issue_signed_proof()
        self.associations.path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(IdentityAssociationError):
            self.associations.list_associations()


if __name__ == "__main__":
    unittest.main()
