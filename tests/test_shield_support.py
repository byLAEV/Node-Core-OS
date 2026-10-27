"""Tests for quorum-backed Shield support evidence bundles."""
from datetime import datetime, timedelta, timezone
import hashlib
import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.security.distributed_defense import (
    SecurityRecordError,
    create_signed_security_event,
)
from node_core.security.shield_support import (
    create_shield_support_certificate,
    verify_shield_support_certificate,
)


class ShieldSupportCertificateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = datetime.now(timezone.utc)
        self.reporters = []
        self.trusted = {}
        for index in range(3):
            store = NodeIdentityStore(Path(self.temp.name) / f"reporter-{index}")
            meta = store.initialize()
            self.reporters.append(store)
            self.trusted[meta["node_id"]] = meta["public_key"]
        self.subject = "sha256:" + "a" * 64

    def _events(self, count=3):
        return [
            create_signed_security_event(
                store,
                event_type="web_abuse_observed",
                subject_id=self.subject,
                observed_at=self.now - timedelta(seconds=1),
                expires_at=self.now + timedelta(minutes=5),
                evidence_sha256=hashlib.sha256(b"synthetic observation").hexdigest(),
                confidence="corroborated",
            )
            for store in self.reporters[:count]
        ]

    def test_three_trusted_reports_create_verifiable_support_certificate(self):
        certificate = create_shield_support_certificate(
            self.subject, self._events(), self.trusted, now=self.now
        )
        self.assertTrue(verify_shield_support_certificate(
            certificate, self.trusted, now=self.now
        ))

    def test_insufficient_quorum_does_not_create_certificate(self):
        with self.assertRaises(SecurityRecordError):
            create_shield_support_certificate(
                self.subject, self._events(2), self.trusted, now=self.now
            )

    def test_tampered_event_or_subject_is_rejected(self):
        certificate = create_shield_support_certificate(
            self.subject, self._events(), self.trusted, now=self.now
        )
        certificate["events"][0]["subject_id"] = "sha256:" + "b" * 64
        self.assertFalse(verify_shield_support_certificate(
            certificate, self.trusted, now=self.now
        ))

    def test_receiver_policy_cannot_be_lowered_by_certificate(self):
        certificate = create_shield_support_certificate(
            self.subject, self._events(), self.trusted, now=self.now
        )
        certificate["minimum_independent_reporters"] = 2
        self.assertFalse(verify_shield_support_certificate(
            certificate, self.trusted, minimum_required_reporters=3, now=self.now
        ))

    def test_expired_certificate_is_rejected(self):
        certificate = create_shield_support_certificate(
            self.subject, self._events(), self.trusted, now=self.now
        )
        later = self.now + timedelta(minutes=6)
        self.assertFalse(verify_shield_support_certificate(
            certificate, self.trusted, now=later
        ))


if __name__ == "__main__":
    unittest.main()
