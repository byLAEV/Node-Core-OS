import socket
import tempfile
import time
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.service import NodePeerService
from node_core.p2p.session import (
    AuthenticatedPeerSession,
    receive_application_message,
    send_application_message,
)
from node_core.p2p.tls_transport import NodeTLSTransport


class ActivePeerSessionRevocationTests(unittest.TestCase):
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

    def test_revoking_one_peer_keeps_other_peer_session_and_listener(self):
        store_c = NodeIdentityStore(Path(self.temp.name) / "node-c")
        meta_c = store_c.initialize()
        tls_c = NodeTLSTransport(store_c)
        cert_c = tls_c.ensure_certificate()

        server = NodePeerService(
            identity_store=self.store_b,
            tls_transport=self.tls_b,
            trusted_peers={
                self.meta_a["node_id"]: self.cert_a,
                meta_c["node_id"]: cert_c,
            },
            host="127.0.0.1",
            port=0,
            timeout_seconds=3,
        )
        host, port = server.start()
        self.addCleanup(server.stop)

        def connect_client(store, tls, expected_server_id, server_certificate):
            raw = socket.create_connection((host, port), timeout=3)
            client_tls = tls.client_context([server_certificate]).wrap_socket(
                raw, server_hostname=None
            )
            client_tls.settimeout(3)
            AuthenticatedPeerSession(
                store, tls, expected_server_id, timeout_seconds=3
            ).establish(client_tls, "initiator")
            return client_tls

        client_a = connect_client(
            self.store_a, self.tls_a, self.meta_b["node_id"], self.cert_b
        )
        client_c = connect_client(
            store_c, tls_c, self.meta_b["node_id"], self.cert_b
        )
        self.addCleanup(client_a.close)
        self.addCleanup(client_c.close)

        deadline = time.monotonic() + 3
        while len(server.active_peers) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(
            {peer["node_id"] for peer in server.active_peers},
            {self.meta_a["node_id"], meta_c["node_id"]},
        )

        closed_count = server.revoke_peer(self.meta_a["node_id"])
        self.assertEqual(closed_count, 1)
        self.assertEqual(server.address, (host, port))
        self.assertEqual(
            {peer["node_id"] for peer in server.active_peers},
            {meta_c["node_id"]},
        )
        try:
            self.assertEqual(client_a.recv(1), b"")
        except OSError:
            pass
        send_application_message(
            client_c,
            {
                "version": 1,
                "type": "STATUS",
                "action": "request",
                "request_id": "still-trusted",
            },
        )
        response = receive_application_message(client_c)
        self.assertEqual(response["type"], "STATUS")
        self.assertEqual(response["request_id"], "still-trusted")

        # The listener remains online but must reject the revoked certificate.
        raw = socket.create_connection((host, port), timeout=3)
        try:
            with self.assertRaises(OSError):
                self.tls_a.client_context([self.cert_b]).wrap_socket(
                    raw, server_hostname=None
                )
        finally:
            raw.close()

    def test_active_session_is_removed_when_service_stops(self):
        server = NodePeerService(
            identity_store=self.store_b,
            tls_transport=self.tls_b,
            trusted_peers={self.meta_a["node_id"]: self.cert_a},
            host="127.0.0.1",
            port=0,
            timeout_seconds=5,
        )
        host, port = server.start()
        client_socket = None
        try:
            client_socket = socket.create_connection((host, port), timeout=3)
            tls_socket = self.tls_a.client_context([self.cert_b]).wrap_socket(
                client_socket, server_hostname=None
            )
            client_socket = None
            tls_socket.settimeout(3)
            client_session = AuthenticatedPeerSession(
                self.store_a, self.tls_a, self.meta_b["node_id"], timeout_seconds=3
            )
            client_session.establish(tls_socket, "initiator")

            deadline = time.monotonic() + 3
            while not server.active_peers and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(len(server.active_peers), 1)
            self.assertEqual(server.active_peers[0]["node_id"], self.meta_a["node_id"])

            server.stop()
            self.assertEqual(server.active_peers, [])
            # Shutdown must close the authenticated socket, not only the listener.
            try:
                received = tls_socket.recv(1)
            except OSError:
                received = b""
            self.assertEqual(received, b"")
            tls_socket.close()
        finally:
            server.stop()
            if client_socket is not None:
                client_socket.close()


if __name__ == "__main__":
    unittest.main()
