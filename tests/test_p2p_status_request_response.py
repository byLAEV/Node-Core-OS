import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.service import NodePeerService
from node_core.p2p.tls_transport import NodeTLSTransport


class P2PStatusRequestResponseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.store_a = NodeIdentityStore(root / "node-a")
        self.store_b = NodeIdentityStore(root / "node-b")
        self.meta_a = self.store_a.initialize()
        self.meta_b = self.store_b.initialize()
        self.tls_a = NodeTLSTransport(self.store_a)
        self.tls_b = NodeTLSTransport(self.store_b)
        self.cert_a = self.tls_a.ensure_certificate()
        self.cert_b = self.tls_b.ensure_certificate()

    def test_authenticated_peer_returns_status_response(self):
        server = NodePeerService(
            identity_store=self.store_b,
            tls_transport=self.tls_b,
            trusted_peers={self.meta_a["node_id"]: self.cert_a},
            host="127.0.0.1",
            port=0,
            timeout_seconds=3,
        )
        host, port = server.start()
        self.addCleanup(server.stop)

        client = NodePeerService(
            identity_store=self.store_a,
            tls_transport=self.tls_a,
            trusted_peers={self.meta_b["node_id"]: self.cert_b},
            timeout_seconds=3,
        )
        result = client.request_status(host, port, self.meta_b["node_id"])

        self.assertEqual(result["node_id"], self.meta_b["node_id"])
        self.assertEqual(result["state"], "running")
        self.assertTrue(result["observed_at"])
        self.assertTrue(result["request_id"])

    def test_status_request_refuses_untrusted_node(self):
        client = NodePeerService(
            identity_store=self.store_a,
            tls_transport=self.tls_a,
            trusted_peers={self.meta_b["node_id"]: self.cert_b},
            timeout_seconds=1,
        )
        with self.assertRaisesRegex(Exception, "trusted-peer"):
            client.request_status("127.0.0.1", 1, "sha256:" + "0" * 64)


if __name__ == "__main__":
    unittest.main()
