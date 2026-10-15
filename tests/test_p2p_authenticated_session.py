import socket
import tempfile
import threading
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.session import (
    AuthenticatedPeerSession,
    MAX_MESSAGE_BYTES,
    PeerSessionError,
    _receive_message,
    _send_message,
)
from node_core.p2p.tls_transport import NodeTLSTransport


class AuthenticatedPeerSessionTests(unittest.TestCase):
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

    def test_length_framed_json_round_trip(self):
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        message = {"type": "STATUS", "value": "ok"}
        worker = threading.Thread(target=_send_message, args=(left, message))
        worker.start()
        self.assertEqual(_receive_message(right), message)
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())

    def test_reject_oversized_message(self):
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        left.sendall((MAX_MESSAGE_BYTES + 1).to_bytes(4, "big"))
        with self.assertRaises(PeerSessionError):
            _receive_message(right)

    def test_mutual_session_authentication_over_tls(self):
        left, right = socket.socketpair()
        results = {}
        errors = []

        def responder():
            try:
                with self.tls_b.server_context([self.cert_a]).wrap_socket(
                    right, server_side=True
                ) as tls_socket:
                    session = AuthenticatedPeerSession(
                        self.store_b, self.tls_b, self.meta_a["node_id"]
                    )
                    results["responder_peer"] = session.establish(tls_socket, "responder")
            except Exception as exc:
                errors.append(exc)

        worker = threading.Thread(target=responder, daemon=True)
        worker.start()
        try:
            with self.tls_a.client_context([self.cert_b]).wrap_socket(
                left, server_hostname=None
            ) as tls_socket:
                session = AuthenticatedPeerSession(
                    self.store_a, self.tls_a, self.meta_b["node_id"]
                )
                results["initiator_peer"] = session.establish(tls_socket, "initiator")
        finally:
            worker.join(timeout=5)
        self.assertFalse(worker.is_alive(), "session handshake timed out")
        self.assertEqual(errors, [])
        self.assertEqual(results["initiator_peer"]["node_id"], self.meta_b["node_id"])
        self.assertEqual(results["responder_peer"]["node_id"], self.meta_a["node_id"])

    def test_expected_peer_mismatch_fails_closed(self):
        left, right = socket.socketpair()
        errors = []

        def responder():
            try:
                with self.tls_b.server_context([self.cert_a]).wrap_socket(
                    right, server_side=True
                ) as tls_socket:
                    AuthenticatedPeerSession(
                        self.store_b, self.tls_b, "sha256:" + "0" * 64
                    ).establish(tls_socket, "responder")
            except Exception as exc:
                errors.append(exc)

        worker = threading.Thread(target=responder, daemon=True)
        worker.start()
        try:
            with self.tls_a.client_context([self.cert_b]).wrap_socket(
                left, server_hostname=None
            ) as tls_socket:
                AuthenticatedPeerSession(
                    self.store_a, self.tls_a, self.meta_b["node_id"]
                ).establish(tls_socket, "initiator")
        except (OSError, PeerSessionError):
            pass
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
