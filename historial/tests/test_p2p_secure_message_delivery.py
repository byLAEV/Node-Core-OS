import tempfile
import time
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.secure_messaging import NodeRSAIdentityStore
from node_core.p2p.service import NodePeerService
from node_core.p2p.tls_transport import NodeTLSTransport


class P2PSecureMessageDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.identity_a = NodeIdentityStore(root / "node-a")
        self.identity_b = NodeIdentityStore(root / "node-b")
        self.meta_a = self.identity_a.initialize()
        self.meta_b = self.identity_b.initialize()
        self.rsa_a = NodeRSAIdentityStore(self.identity_a)
        self.rsa_b = NodeRSAIdentityStore(self.identity_b)
        self.rsa_a.initialize()
        self.rsa_b.initialize()
        self.tls_a = NodeTLSTransport(self.identity_a)
        self.tls_b = NodeTLSTransport(self.identity_b)
        self.cert_a = self.tls_a.ensure_certificate()
        self.cert_b = self.tls_b.ensure_certificate()

    def test_message_is_received_and_signed_receipt_is_verified_over_authenticated_p2p(self):
        accepted_by_callback = []
        server = NodePeerService(
            self.identity_b,
            self.tls_b,
            {self.meta_a["node_id"]: self.cert_a},
            host="127.0.0.1",
            port=0,
            timeout_seconds=5,
            rsa_identity_store=self.rsa_b,
            trusted_rsa_public_keys={
                self.meta_a["node_id"]: self.rsa_a.public_key_pem()
            },
            on_message=lambda peer, message_id, text: accepted_by_callback.append(
                (peer["node_id"], message_id, text)
            ),
        )
        host, port = server.start()
        self.addCleanup(server.stop)

        client = NodePeerService(
            self.identity_a,
            self.tls_a,
            {self.meta_b["node_id"]: self.cert_b},
            timeout_seconds=5,
            rsa_identity_store=self.rsa_a,
        )
        ack = client.send_secure_message(
            host, port, self.meta_b["node_id"], self.rsa_b.public_key_pem(),
            "Hola nodo B, prueba de recepción cifrada.",
        )

        self.assertEqual(ack["type"], "MESSAGE_ACK")
        self.assertEqual(ack["status"], "accepted")
        self.assertEqual(ack["sender_node_id"], self.meta_a["node_id"])
        self.assertEqual(ack["receiver_node_id"], self.meta_b["node_id"])
        self.assertTrue(accepted_by_callback)
        self.assertEqual(accepted_by_callback[0][0], self.meta_a["node_id"])
        self.assertEqual(accepted_by_callback[0][2], "Hola nodo B, prueba de recepción cifrada.")

        inbox = server.received_messages
        self.assertEqual(len(inbox), 1)
        self.assertEqual(inbox[0]["text"], "Hola nodo B, prueba de recepción cifrada.")
        self.assertEqual(inbox[0]["sender_node_id"], self.meta_a["node_id"])
        self.assertEqual(inbox[0]["message_id"], ack["message_id"])


if __name__ == "__main__":
    unittest.main()
