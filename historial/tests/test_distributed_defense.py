"""Tests for signed security events, revocation snapshots and quorum gating."""
from datetime import datetime, timedelta, timezone
import hashlib
import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.security.distributed_defense import (
    SecurityRecordError,
    create_signed_revocation_snapshot,
    create_signed_security_event,
    should_quarantine,
    verify_revocation_snapshot,
    verify_signed_security_event,
)


class DistributedDefensePrimitiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = NodeIdentityStore(Path(self.temp.name) / "node")
        self.meta = self.store.initialize()
        self.trusted = {self.meta["node_id"]: self.meta["public_key"]}
        self.now = datetime.now(timezone.utc)

    def test_signed_event_is_accepted_from_trusted_reporter(self):
        event = create_signed_security_event(
            self.store, event_type="tls_invalid_signature", subject_id="node:target",
            observed_at=self.now, expires_at=self.now + timedelta(minutes=5),
            evidence_sha256=hashlib.sha256(b"synthetic evidence").hexdigest(),
            confidence="corroborated",
        )
        self.assertTrue(verify_signed_security_event(event, self.trusted, now=self.now))

    def test_tampered_or_untrusted_event_is_rejected(self):
        event = create_signed_security_event(
            self.store, event_type="tls_invalid_signature", subject_id="node:target",
            observed_at=self.now, expires_at=self.now + timedelta(minutes=5),
            evidence_sha256=hashlib.sha256(b"evidence").hexdigest(),
        )
        event["subject_id"] = "node:innocent"
        self.assertFalse(verify_signed_security_event(event, self.trusted, now=self.now))
        event["subject_id"] = "node:target"
        self.assertFalse(verify_signed_security_event(event, {}, now=self.now))

    def test_expired_event_is_rejected(self):
        event = create_signed_security_event(
            self.store, event_type="tls_invalid_signature", subject_id="node:target",
            observed_at=self.now - timedelta(hours=2), expires_at=self.now - timedelta(hours=1),
            evidence_sha256=hashlib.sha256(b"evidence").hexdigest(),
        )
        self.assertFalse(verify_signed_security_event(event, self.trusted, now=self.now))

    def test_signed_revocation_snapshot_and_anti_rollback(self):
        snap = create_signed_revocation_snapshot(
            self.store, sequence=4, issued_at=self.now - timedelta(seconds=1),
            expires_at=self.now + timedelta(minutes=10), revoked_node_ids=["node:bad"],
        )
        self.assertTrue(verify_revocation_snapshot(snap, self.trusted, last_sequence=3, now=self.now))
        self.assertFalse(verify_revocation_snapshot(snap, self.trusted, last_sequence=4, now=self.now))
        snap["revoked_node_ids"] = []
        self.assertFalse(verify_revocation_snapshot(snap, self.trusted, last_sequence=3, now=self.now))

    def _reporter(self, name):
        store = NodeIdentityStore(Path(self.temp.name) / name)
        meta = store.initialize()
        return store, meta

    def _event(self, store, confidence="corroborated"):
        return create_signed_security_event(
            store, event_type="tls_invalid_signature", subject_id="node:bad",
            observed_at=self.now - timedelta(seconds=1),
            expires_at=self.now + timedelta(minutes=5),
            evidence_sha256=hashlib.sha256(b"same synthetic evidence").hexdigest(),
            confidence=confidence,
        )

    def test_single_reporter_cannot_trigger_quarantine_even_if_repeated(self):
        store, meta = self._reporter("reporter-one")
        event = self._event(store, "confirmed")
        trusted = {meta["node_id"]: meta["public_key"]}
        self.assertFalse(should_quarantine("node:bad", [event], trusted, now=self.now))
        self.assertFalse(should_quarantine("node:bad", [event] * 5, trusted, now=self.now))

    def test_distinct_signed_reporters_can_trigger_quarantine(self):
        stores = [self._reporter(f"reporter-{i}") for i in range(3)]
        trusted = {meta["node_id"]: meta["public_key"] for _, meta in stores}
        events = [self._event(store) for store, _ in stores]
        self.assertTrue(should_quarantine("node:bad", events, trusted, now=self.now))

    def test_untrusted_fabricated_report_cannot_trigger_quarantine(self):
        store, meta = self._reporter("reporter-known")
        event = self._event(store)
        self.assertFalse(should_quarantine("node:bad", [event], {}, now=self.now))
        forged = dict(event)
        forged["reporter_node_id"] = "sha256:" + "0" * 64
        self.assertFalse(should_quarantine("node:bad", [forged], {meta["node_id"]: meta["public_key"]}, now=self.now))

    def test_quarantine_threshold_cannot_be_one(self):
        with self.assertRaises(SecurityRecordError):
            should_quarantine("node:bad", [], {}, minimum_independent_reporters=1)


if __name__ == "__main__":
    unittest.main()
