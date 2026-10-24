import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.message_store import P2PMessageStore
from node_core.p2p.service import NodePeerService
from node_core.p2p.tls_transport import NodeTLSTransport


class P2PMessageDeliveryTests(unittest.TestCase):
    def test_message_is_delivered_over_authenticated_tls_and_saved_by_recipient(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity_a = NodeIdentityStore(root / "a")
            identity_b = NodeIdentityStore(root / "b")
            metadata_a = identity_a.initialize()
            metadata_b = identity_b.initialize()
            tls_a = NodeTLSTransport(identity_a)
            tls_b = NodeTLSTransport(identity_b)
            cert_a = tls_a.ensure_certificate()
            cert_b = tls_b.ensure_certificate()
            inbox_b = P2PMessageStore(root / "b")

            def on_message(peer, message):
                return inbox_b.record_incoming(
                    from_node_id=peer["node_id"],
                    recipient_node_id=message["recipient_node_id"],
                    local_node_id=metadata_b["node_id"],
                    request_id=message["request_id"],
                    text=message["text"],
                    sent_at=message["sent_at"],
                )

            server = NodePeerService(
                identity_b, tls_b, {metadata_a["node_id"]: cert_a},
                host="127.0.0.1", port=0, timeout_seconds=3,
                on_message=on_message,
            )
            _, port = server.start()
            self.addCleanup(server.stop)
            client = NodePeerService(
                identity_a, tls_a, {metadata_b["node_id"]: cert_b},
                timeout_seconds=3,
            )
            sent_at = datetime.now(timezone.utc).isoformat()
            receipt = client.request_message(
                "127.0.0.1", port, metadata_b["node_id"],
                "P2P hello", sent_at=sent_at,
            )
            self.assertEqual(receipt["node_id"], metadata_b["node_id"])
            self.assertEqual(receipt["status"], "received")
            self.assertTrue(receipt["message_id"])
            inbox = inbox_b.list_inbox()
            self.assertEqual(len(inbox), 1)
            self.assertEqual(inbox[0]["from_node_id"], metadata_a["node_id"])
            self.assertEqual(inbox[0]["text"], "P2P hello")
            self.assertEqual(inbox[0]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
