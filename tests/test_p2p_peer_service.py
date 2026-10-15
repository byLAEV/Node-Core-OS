import tempfile
import threading
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.service import NodePeerService, PeerServiceError
from node_core.p2p.tls_transport import NodeTLSTransport


class NodePeerServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.store_a = NodeIdentityStore(root / "a")
        self.store_b = NodeIdentityStore(root / "b")
        self.meta_a = self.store_a.initialize()
        self.meta_b = self.store_b.initialize()
        self.tls_a = NodeTLSTransport(self.store_a)
        self.tls_b = NodeTLSTransport(self.store_b)
        self.cert_a = self.tls_a.ensure_certificate()
        self.cert_b = self.tls_b.ensure_certificate()

    def test_listener_and_client_complete_authenticated_session(self):
        accepted = []
        accepted_event = threading.Event()
        def on_peer(peer, _socket):
            accepted.append(peer)
            accepted_event.set()

        server = NodePeerService(
            self.store_b,
            self.tls_b,
            {self.meta_a["node_id"]: self.cert_a},
            host="127.0.0.1",
            port=0,
            timeout_seconds=3,
            on_peer=on_peer,
        )
        address = server.start()
        self.addCleanup(server.stop)
        client = NodePeerService(
            self.store_a,
            self.tls_a,
            {self.meta_b["node_id"]: self.cert_b},
            timeout_seconds=3,
        )
        peer = client.connect(address[0], address[1], self.meta_b["node_id"])
        self.assertEqual(peer["node_id"], self.meta_b["node_id"])
        self.assertTrue(accepted_event.wait(3))
        self.assertEqual(accepted[0]["node_id"], self.meta_a["node_id"])

    def test_client_rejects_peer_not_in_allowlist(self):
        client = NodePeerService(
            self.store_a,
            self.tls_a,
            {self.meta_b["node_id"]: self.cert_b},
        )
        with self.assertRaises(PeerServiceError):
            client.connect("127.0.0.1", 1, "sha256:" + "0" * 64)

    def test_service_requires_explicit_trust(self):
        with self.assertRaises(ValueError):
            NodePeerService(self.store_a, self.tls_a, {})


if __name__ == "__main__":
    unittest.main()
