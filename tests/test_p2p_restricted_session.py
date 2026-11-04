import multiprocessing
import socket
import struct
import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.discovery import create_announcement, parse_announcement
from node_core.p2p.restricted_session import (
    RestrictedPeerSession,
    RestrictedSessionAdmission,
    RestrictedSessionError,
    _validate_request,
    _receive_restricted,
    MAX_RESTRICTED_FRAME_BYTES,
)
from node_core.p2p.tls_transport import NodeTLSTransport
from node_core.p2p.trust_store import PeerTrustStore


def _restricted_server_process(server_dir, client_node_id, client_certificate, result_queue):
    store = NodeIdentityStore(Path(server_dir))
    transport = NodeTLSTransport(store)
    transport.ensure_certificate()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    server_announcement = create_announcement(
        store, "127.0.0.1", listener.getsockname()[1]
    )
    result_queue.put(("ready", listener.getsockname()[1], server_announcement))
    try:
        raw, _ = listener.accept()
        with transport.server_context([client_certificate]).wrap_socket(raw, server_side=True) as tls_socket:
            RestrictedPeerSession(store, transport).serve_one(
                tls_socket, client_node_id,
                is_revoked=lambda _node_id: False,
                availability="available",
            )
        result_queue.put(("done", "ok"))
    except Exception as exc:
        result_queue.put(("error", repr(exc)))
        raise
    finally:
        listener.close()


class RestrictedPeerSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.client_store = NodeIdentityStore(root / "client")
        self.server_store = NodeIdentityStore(root / "server")
        self.client_meta = self.client_store.initialize()
        self.server_meta = self.server_store.initialize()
        self.client_tls = NodeTLSTransport(self.client_store)
        self.server_tls = NodeTLSTransport(self.server_store)
        self.client_cert = self.client_tls.ensure_certificate()
        self.server_cert = self.server_tls.ensure_certificate()

    def test_two_independent_linux_processes_authenticate_and_exchange_only_status(self):
        client_announcement = parse_announcement(
            create_announcement(self.client_store, "127.0.0.1", 0)
        )
        ctx = multiprocessing.get_context("spawn")
        queue = ctx.Queue()
        process = ctx.Process(
            target=_restricted_server_process,
            args=(
                str(self.server_store.data_dir),
                self.server_meta["node_id"],
                client_announcement.tls_certificate_pem,
                queue,
            ),
        )
        process.start()
        try:
            state, port, server_announcement_payload = queue.get(timeout=10)
            self.assertEqual(state, "ready")
            server_announcement = parse_announcement(server_announcement_payload)
            response = RestrictedPeerSession(self.client_store, self.client_tls).request_status(
                "127.0.0.1", port, self.server_meta["node_id"],
                server_announcement.tls_certificate_pem,
            )
            self.assertEqual(response["type"], "IDENTITY_STATUS_RESPONSE")
            self.assertEqual(response["node_id"], self.server_meta["node_id"])
            self.assertEqual(response["availability"], "available")
            state, result = queue.get(timeout=10)
            self.assertEqual((state, result), ("done", "ok"))
        finally:
            process.join(timeout=10)
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        self.assertEqual(process.exitcode, 0)
        self.assertEqual(PeerTrustStore(self.client_store.data_dir).list_peers(), [])
        self.assertEqual(PeerTrustStore(self.server_store.data_dir).list_peers(), [])

    def test_rejects_application_and_unknown_protocol_types(self):
        for message_type in ("MESSAGE", "PEERS", "UNKNOWN"):
            with self.subTest(message_type=message_type):
                with self.assertRaises(RestrictedSessionError):
                    _validate_request({
                        "version": 1, "type": message_type, "request_id": "a" * 32,
                    })

    def test_rejects_extra_fields_and_invalid_request_ids(self):
        with self.assertRaises(RestrictedSessionError):
            _validate_request({
                "version": 1, "type": "IDENTITY_STATUS_REQUEST",
                "request_id": "a" * 32, "extra": "not-allowed",
            })
        with self.assertRaises(RestrictedSessionError):
            _validate_request({
                "version": 1, "type": "IDENTITY_STATUS_REQUEST", "request_id": "bad",
            })

    def test_restricted_decoder_rejects_duplicate_keys_and_oversized_frames(self):
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        duplicate = b'{"version":1,"type":"IDENTITY_STATUS_REQUEST","type":"MESSAGE","request_id":"' + b"a" * 32 + b'"}'
        left.sendall(struct.pack("!I", len(duplicate)) + duplicate)
        with self.assertRaises(RestrictedSessionError):
            _receive_restricted(right)

        left2, right2 = socket.socketpair()
        self.addCleanup(left2.close)
        self.addCleanup(right2.close)
        left2.sendall(struct.pack("!I", MAX_RESTRICTED_FRAME_BYTES + 1))
        with self.assertRaises(RestrictedSessionError):
            _receive_restricted(right2)

    def test_admission_limits_workers_and_source_rate(self):
        admission = RestrictedSessionAdmission(max_workers=1, requests_per_minute=2)
        self.assertTrue(admission.admit("192.0.2.10", now=10))
        self.assertTrue(admission.admit("192.0.2.10", now=11))
        self.assertFalse(admission.admit("192.0.2.10", now=12))
        self.assertTrue(admission.acquire_worker())
        self.assertFalse(admission.acquire_worker())
        admission.release_worker()
        self.assertTrue(admission.acquire_worker())
        admission.release_worker()


if __name__ == "__main__":
    unittest.main()
