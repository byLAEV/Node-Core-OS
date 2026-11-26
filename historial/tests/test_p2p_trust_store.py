import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.tls_transport import NodeTLSTransport
from node_core.p2p.trust_store import PeerTrustStore, PeerTrustStoreError


class PeerTrustStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.store_a = NodeIdentityStore(root / "a")
        self.store_b = NodeIdentityStore(root / "b")
        self.meta_a = self.store_a.initialize()
        self.meta_b = self.store_b.initialize()
        self.cert_a = NodeTLSTransport(self.store_a).ensure_certificate()
        self.cert_b = NodeTLSTransport(self.store_b).ensure_certificate()
        self.trust = PeerTrustStore(root / "data")

    def test_add_is_persistent_and_idempotent(self):
        first = self.trust.add(self.meta_a["node_id"], self.cert_a, "node-a")
        second = self.trust.add(self.meta_a["node_id"], self.cert_a, "node-a")
        self.assertEqual(first["fingerprint_sha256"], second["fingerprint_sha256"])
        reloaded = PeerTrustStore(self.trust.data_dir)
        self.assertEqual(
            reloaded.trusted_certificates()[self.meta_a["node_id"]], self.cert_a
        )
        self.assertEqual(reloaded.get(self.meta_a["node_id"])["status"], "trusted")

    def test_reject_certificate_for_wrong_node_id(self):
        with self.assertRaises(PeerTrustStoreError):
            self.trust.add(self.meta_a["node_id"], self.cert_b)

    def test_reject_unapproved_certificate_replacement(self):
        self.trust.add(self.meta_a["node_id"], self.cert_a)
        # A different valid certificate for the same key can be produced by a
        # second store only if the private identity is shared; use node B here
        # to confirm a different certificate cannot be bound to node A's ID.
        with self.assertRaises(PeerTrustStoreError):
            self.trust.add(self.meta_a["node_id"], self.cert_b)

    def test_revocation_removes_peer_from_active_allowlist(self):
        self.trust.add(self.meta_a["node_id"], self.cert_a)
        revoked = self.trust.revoke(self.meta_a["node_id"])
        self.assertEqual(revoked["status"], "revoked")
        self.assertNotIn(self.meta_a["node_id"], self.trust.trusted_certificates())
        self.assertEqual(self.trust.get(self.meta_a["node_id"])["status"], "revoked")

    def test_corrupt_store_fails_closed(self):
        self.trust.path.parent.mkdir(parents=True)
        self.trust.path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(PeerTrustStoreError):
            self.trust.load()

    def test_empty_store_is_valid_and_has_no_trusted_peers(self):
        self.assertEqual(self.trust.trusted_certificates(), {})
        self.assertEqual(self.trust.list_peers(), [])


if __name__ == "__main__":
    unittest.main()
