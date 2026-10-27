"""Regression tests for the synthetic enterprise identity defense workflow."""
import unittest
import hashlib

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.enterprise_identity_defense_simulation import (
    EnterpriseAsset,
    EnterprisePool,
    IdentityNode,
    run_simulation,
    verify_asset_report,
    verify_node_votes,
)


class EnterpriseIdentityDefenseSimulationTests(unittest.TestCase):
    def setUp(self):
        self.pool = EnterprisePool("pool-test", Ed25519PrivateKey.generate())
        self.asset = EnterpriseAsset("web2:service.example.test")
        self.certificate = self.pool.issue_certificate(
            self.asset.asset_id, "web2_domain", self.asset.public_key,
            "tls_and_application", now=1_800_000_000,
        )

    def test_complete_synthetic_scenario(self):
        result = run_simulation()
        self.assertTrue(result["quorum_reached"])
        self.assertEqual(result["assets_registered"], 2)
        self.assertEqual(result["installation_reports_verified"], 2)
        self.assertFalse(result["external_network_contacted"])
        self.assertFalse(result["real_assets_touched"])

    def test_valid_installation_report_is_accepted(self):
        report = self.asset.install(self.certificate)
        self.assertTrue(verify_asset_report(report, self.certificate, self.pool, now=1_800_000_001))

    def test_tampered_installation_report_is_rejected(self):
        report = self.asset.install(self.certificate)
        report["payload"]["asset_id"] = "web2:attacker.example.test"
        self.assertFalse(verify_asset_report(report, self.certificate, self.pool, now=1_800_000_001))

    def test_expired_certificate_is_rejected(self):
        report = self.asset.install(self.certificate)
        self.assertFalse(verify_asset_report(report, self.certificate, self.pool, now=1_900_000_000))

    def test_certificate_bound_to_other_asset_is_rejected(self):
        other = EnterpriseAsset("device:other")
        with self.assertRaises(ValueError):
            other.install(self.certificate)

    def test_quorum_requires_distinct_trusted_nodes(self):
        node = IdentityNode("node-a", Ed25519PrivateKey.generate())
        digest = hashlib.sha256(b"synthetic incident").hexdigest()
        vote = node.vote(digest, "containment_recommended")
        self.assertFalse(verify_node_votes([vote, vote, vote], {node.node_id: node.public_key}, digest, 2))

    def test_quorum_rejects_tampered_or_untrusted_vote(self):
        nodes = [IdentityNode("node-a", Ed25519PrivateKey.generate()),
                 IdentityNode("node-b", Ed25519PrivateKey.generate())]
        digest = hashlib.sha256(b"synthetic incident").hexdigest()
        votes = [node.vote(digest, "containment_recommended") for node in nodes]
        trusted = {node.node_id: node.public_key for node in nodes}
        self.assertTrue(verify_node_votes(votes, trusted, digest, 2))
        votes[1]["payload"]["decision"] = "allow"
        self.assertFalse(verify_node_votes(votes, trusted, digest, 2))

    def test_quorum_threshold_one_is_forbidden(self):
        with self.assertRaises(ValueError):
            verify_node_votes([], {}, "digest", 1)


if __name__ == "__main__":
    unittest.main()
