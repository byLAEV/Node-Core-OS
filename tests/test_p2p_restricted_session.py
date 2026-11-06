import multiprocessing
import socket
import ssl
import struct
import tempfile
import time
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.discovery import create_announcement, parse_announcement
from node_core.p2p.restricted_session import (
    RestrictedPeerService,
    RestrictedPeerSession,
    RestrictedSessionAdmission,
    RestrictedSessionError,
    _validate_request,
    _receive_restricted,
    MAX_RESTRICTED_FRAME_BYTES,
)
from node_core.p2p.session import AuthenticatedPeerSession
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
                self.client_meta["node_id"],
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

    def _wait_for_service_idle(self, service, timeout=3.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with service._connections_lock:
                connections = bool(service._connections)
            with service._workers_lock:
                workers = bool(service._workers)
            if not connections and not workers:
                return
            time.sleep(0.01)
        self.fail("RestrictedPeerService did not release its connection and worker.")

    def test_service_handles_real_authenticated_request_and_releases_worker(self):
        service = RestrictedPeerService(
            self.server_store,
            self.server_tls,
            lambda: {self.client_meta["node_id"]: self.client_cert},
            is_revoked=lambda _node_id: False,
            timeout_seconds=5.0,
            handshake_timeout_seconds=10.0,
        )
        host, port = service.start()
        try:
            response = RestrictedPeerSession(
                self.client_store, self.client_tls, timeout_seconds=10.0
            ).request_status(
                host, port, self.server_meta["node_id"], self.server_cert
            )
            self.assertEqual(response["node_id"], self.server_meta["node_id"])
            self.assertEqual(response["availability"], "available")
        finally:
            service.stop()
        self._wait_for_service_idle(service)
        self.assertTrue(service.admission.acquire_worker())
        service.admission.release_worker()
        self.assertEqual(PeerTrustStore(self.client_store.data_dir).list_peers(), [])
        self.assertEqual(PeerTrustStore(self.server_store.data_dir).list_peers(), [])

    def test_handshake_timeout_releases_worker_and_listener_recovers(self):
        service = RestrictedPeerService(
            self.server_store,
            self.server_tls,
            lambda: {self.client_meta["node_id"]: self.client_cert},
            is_revoked=lambda _node_id: False,
            timeout_seconds=2.0,
            handshake_timeout_seconds=0.2,
            max_workers=1,
        )
        host, port = service.start()
        stalled = socket.create_connection((host, port), timeout=2.0)
        try:
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                with service._connections_lock:
                    pending = bool(service._connections)
                with service._workers_lock:
                    workers = bool(service._workers)
                if not pending and not workers:
                    break
                time.sleep(0.01)
            self.assertFalse(pending)
            self.assertFalse(workers)
            self.assertTrue(service.admission.acquire_worker())
            service.admission.release_worker()

            response = RestrictedPeerSession(
                self.client_store, self.client_tls, timeout_seconds=5.0
            ).request_status(
                host, port, self.server_meta["node_id"], self.server_cert
            )
            self.assertEqual(response["availability"], "available")
        finally:
            stalled.close()
            service.stop()
        self._wait_for_service_idle(service)

    def test_stop_closes_client_stalled_before_tls_authentication(self):
        service = RestrictedPeerService(
            self.server_store,
            self.server_tls,
            lambda: {self.client_meta["node_id"]: self.client_cert},
            is_revoked=lambda _node_id: False,
            timeout_seconds=20.0,
            handshake_timeout_seconds=60.0,
        )
        host, port = service.start()
        stalled = socket.create_connection((host, port), timeout=2.0)
        try:
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                with service._connections_lock:
                    accepted = bool(service._connections)
                if accepted:
                    break
                time.sleep(0.01)
            self.assertTrue(accepted)
            service.stop()
            stalled.settimeout(2.0)
            self.assertEqual(stalled.recv(1), b"")
        finally:
            stalled.close()
            service.stop()
        self._wait_for_service_idle(service)

    def test_revoke_closes_authenticated_session_before_status_request(self):
        service = RestrictedPeerService(
            self.server_store,
            self.server_tls,
            lambda: {self.client_meta["node_id"]: self.client_cert},
            is_revoked=lambda _node_id: False,
            timeout_seconds=10.0,
            handshake_timeout_seconds=10.0,
        )
        host, port = service.start()
        raw = socket.create_connection((host, port), timeout=5.0)
        tls_socket = None
        try:
            tls_socket = self.client_tls.client_context([self.server_cert]).wrap_socket(
                raw, server_hostname=None
            )
            AuthenticatedPeerSession(
                self.client_store,
                self.client_tls,
                self.server_meta["node_id"],
                timeout_seconds=5.0,
            ).establish(tls_socket, "initiator")
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                with service._active_lock:
                    active = bool(service._active.get(self.client_meta["node_id"]))
                if active:
                    break
                time.sleep(0.01)
            self.assertTrue(active)
            self.assertEqual(service.revoke_peer(self.client_meta["node_id"]), 1)
            tls_socket.settimeout(2.0)
            with self.assertRaises((OSError, ssl.SSLError)):
                tls_socket.recv(1)
        finally:
            if tls_socket is not None:
                tls_socket.close()
            else:
                raw.close()
            service.stop()
        self._wait_for_service_idle(service)


if __name__ == "__main__":
    unittest.main()
