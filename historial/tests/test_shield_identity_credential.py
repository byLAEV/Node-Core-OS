"""Tests for quorum-signed Shield identity credentials."""
from datetime import datetime, timedelta, timezone
import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.security.shield_identity_credential import (
    create_quorum_identity_credential,
    verify_quorum_identity_credential,
)


class ShieldIdentityCredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = datetime.now(timezone.utc)
        self.issuers = []
        self.trusted = {}
        for index in range(3):
            store = NodeIdentityStore(Path(self.temp.name) / f"issuer-{index}")
            metadata = store.initialize()
            self.issuers.append(store)
            self.trusted[metadata["node_id"]] = metadata["public_key"]
        subject = NodeIdentityStore(Path(self.temp.name) / "subject")
        subject_metadata = subject.initialize()
        self.subject_id = subject_metadata["node_id"]
        self.subject_public_key = subject_metadata["public_key"]

    def _credential(self):
        return create_quorum_identity_credential(
            subject_public_key_hex=self.subject_public_key,
            subject_type="web_application",
            scopes=["https:access", "shield:report"],
            issuer_stores=self.issuers,
            minimum_issuers=3,
            now=self.now,
            lifetime=timedelta(days=10),
        )

    def test_three_trusted_issuers_sign_service_credential(self):
        credential = self._credential()
        self.assertTrue(verify_quorum_identity_credential(
            credential, self.trusted, minimum_required_issuers=3,
            required_scope="https:access", expected_subject_id=self.subject_id,
            now=self.now,
        ))

    def test_two_signatures_do_not_meet_quorum(self):
        credential = self._credential()
        credential["issuer_signatures"] = credential["issuer_signatures"][:2]
        self.assertFalse(verify_quorum_identity_credential(
            credential, self.trusted, minimum_required_issuers=3, now=self.now
        ))

    def test_tampered_scope_is_rejected(self):
        credential = self._credential()
        credential["scopes"].append("admin:all")
        self.assertFalse(verify_quorum_identity_credential(
            credential, self.trusted, minimum_required_issuers=3, now=self.now
        ))

    def test_expired_credential_is_rejected(self):
        credential = self._credential()
        self.assertFalse(verify_quorum_identity_credential(
            credential, self.trusted, minimum_required_issuers=3,
            now=self.now + timedelta(days=11),
        ))

    def test_untrusted_issuer_signature_does_not_count(self):
        credential = self._credential()
        credential["issuer_signatures"][0]["issuer_public_key"] = "00" * 32
        self.assertFalse(verify_quorum_identity_credential(
            credential, self.trusted, minimum_required_issuers=3, now=self.now
        ))

    def test_required_scope_is_enforced(self):
        credential = self._credential()
        self.assertFalse(verify_quorum_identity_credential(
            credential, self.trusted, minimum_required_issuers=3,
            required_scope="database:admin", now=self.now,
        ))

    def test_duplicate_issuer_nodes_cannot_issue_quorum(self):
        with self.assertRaises(ValueError):
            create_quorum_identity_credential(
                subject_public_key_hex=self.subject_public_key,
                subject_type="service",
                scopes=["https:access"],
                issuer_stores=[self.issuers[0], self.issuers[0], self.issuers[1]],
                minimum_issuers=3,
                now=self.now,
            )


if __name__ == "__main__":
    unittest.main()
