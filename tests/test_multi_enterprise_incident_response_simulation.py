"""Regression tests for multi-enterprise incident response simulation."""
import hashlib
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.multi_enterprise_incident_response_simulation import (
    EnterpriseAsset,
    EnterprisePool,
    IdentityNode,
    run_simulation,
    verify_quorum,
)


class MultiEnterpriseIncidentResponseTests(unittest.TestCase):
    def setUp(self):
        self.pool_a = EnterprisePool("pool-a", Ed25519PrivateKey.generate())
        self.pool_b = EnterprisePool("pool-b", Ed25519PrivateKey.generate())
        self.asset = EnterpriseAsset("web2:service-a.example.test", "pool-a", "web2_domain")
        self.certificate = self.pool_a.issue_certificate(
            self.asset.asset_id, self.asset.asset_type, self.asset.public_key,
            now=1_800_000_000, lifetime_seconds=3600,
        )

    def test_complete_multi_enterprise_scenario(self):
        result = run_simulation()
        self.assertEqual(result["enterprise_pools"], 2)
        self.assertEqual(result["registered_assets"], 2)
        self.assertEqual(result["duplicate_event_result"], "duplicate_ignored")
        self.assertTrue(result["quorum_reached"])
        self.assertTrue(result["tampered_incident_rejected"])
        self.assertFalse(result["response_applied_to_real_asset"])

    def test_cross_pool_certificate_is_rejected(self):
        with self.assertRaises(PermissionError):
            self.asset.install(self.pool_b.issue_certificate(
                self.asset.asset_id, self.asset.asset_type, self.asset.public_key,
                now=1_800_000_000,
            ))

    def test_cross_pool_installation_registration_is_rejected(self):
        report = self.asset.install(self.certificate)
        with self.assertRaises(PermissionError):
            self.pool_b.register_installation(report, self.certificate, now=1_800_000_001)

    def test_duplicate_installation_event_is_idempotent(self):
        report = self.asset.install(self.certificate)
        first = self.pool_a.register_installation(report, self.certificate, now=1_800_000_001)
        second = self.pool_a.register_installation(report, self.certificate, now=1_800_000_001)
        self.assertEqual(first, "registered")
        self.assertEqual(second, "duplicate_ignored")
        self.assertEqual(len(self.pool_a.assets), 1)

    def test_tampered_incident_is_rejected(self):
        self.asset.install(self.certificate)
        incident = self.asset.report_incident("synthetic_test", "evidence")
        incident["payload"]["incident_type"] = "tampered"
        with self.assertRaises(ValueError):
            self.pool_a.accept_incident(incident, self.certificate, now=1_800_000_001)

    def test_expired_certificate_is_rejected(self):
        report = self.asset.install(self.certificate)
        with self.assertRaises(ValueError):
            self.pool_a.register_installation(report, self.certificate, now=1_900_000_000)

    def test_quorum_needs_two_distinct_trusted_nodes(self):
        node = IdentityNode("node-a", Ed25519PrivateKey.generate())
        digest = hashlib.sha256(b"incident").hexdigest()
        vote = node.assess(digest, "containment_recommended")
        self.assertFalse(verify_quorum([vote, vote, vote], {"node-a": node.public_key}, digest, 2))

    def test_quorum_rejects_tampered_or_untrusted_votes(self):
        node_a = IdentityNode("node-a", Ed25519PrivateKey.generate())
        node_b = IdentityNode("node-b", Ed25519PrivateKey.generate())
        digest = hashlib.sha256(b"incident").hexdigest()
        votes = [node_a.assess(digest, "containment_recommended"),
                 node_b.assess(digest, "containment_recommended")]
        trusted = {"node-a": node_a.public_key, "node-b": node_b.public_key}
        self.assertTrue(verify_quorum(votes, trusted, digest, 2))
        votes[1]["payload"]["recommendation"] = "ignore"
        self.assertFalse(verify_quorum(votes, trusted, digest, 2))

    def test_quorum_threshold_one_is_forbidden(self):
        with self.assertRaises(ValueError):
            verify_quorum([], {}, "digest", 1)


if __name__ == "__main__":
    unittest.main()
