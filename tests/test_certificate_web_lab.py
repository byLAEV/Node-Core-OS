"""Loopback web-service security lab using Node Core OS mutual TLS.

All identities/certificates are synthetic and stored in a temporary directory.
The HTTP service binds only to 127.0.0.1; no external devices or websites are
contacted. These tests assess pinned-certificate transport, not browser PKI.
"""
import http.client
import json
import socket
import ssl
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.tls_transport import NodeTLSTransport


class _QuietThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # Expected when an adversarial TLS handshake is rejected.
        pass


def _handler_for(transport, expected_client_id):
    class SecurePageHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_GET(self):
            if self.path != "/health":
                body = b'{"error":"not_found"}'
                self.send_response(404)
            else:
                # TLS trust and application-level node-ID authorization are separate.
                peer = transport.verify_peer_identity(
                    self.connection, expected_node_id=expected_client_id
                )
                body = json.dumps({
                    "service": "Node Core OS protected test page",
                    "authenticated_node": peer["node_id"],
                    "status": "PASS",
                }, sort_keys=True).encode("utf-8")
                self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return SecurePageHandler


class CertificateWebLabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)

        self.server_store = NodeIdentityStore(root / "server")
        self.client_store = NodeIdentityStore(root / "client")
        self.attacker_store = NodeIdentityStore(root / "attacker")

        self.server_meta = self.server_store.initialize()
        self.client_meta = self.client_store.initialize()
        self.attacker_meta = self.attacker_store.initialize()

        self.server_tls = NodeTLSTransport(self.server_store)
        self.client_tls = NodeTLSTransport(self.client_store)
        self.attacker_tls = NodeTLSTransport(self.attacker_store)

        self.server_cert = self.server_tls.ensure_certificate()
        self.client_cert = self.client_tls.ensure_certificate()
        self.attacker_cert = self.attacker_tls.ensure_certificate()

        self.servers = []
        self.threads = []
        self.addCleanup(self._shutdown_servers)

    def _start_page(self, tls_transport, server_cert, trusted_client_cert, expected_client_id):
        httpd = _QuietThreadingHTTPServer(
            ("127.0.0.1", 0),
            _handler_for(tls_transport, expected_client_id),
        )
        httpd.socket = tls_transport.server_context([trusted_client_cert]).wrap_socket(
            httpd.socket, server_side=True
        )
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        self.servers.append(httpd)
        self.threads.append(thread)
        return httpd.server_address[1]

    def _shutdown_servers(self):
        for server in self.servers:
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join(timeout=3)

    def _get(self, port, client_transport, trusted_server_cert):
        context = client_transport.client_context([trusted_server_cert])
        conn = http.client.HTTPSConnection(
            "127.0.0.1", port, context=context, timeout=3
        )
        try:
            conn.request("GET", "/health", headers={"Connection": "close"})
            response = conn.getresponse()
            return response.status, response.read()
        finally:
            conn.close()

    def test_trusted_node_can_load_protected_web_page(self):
        port = self._start_page(
            self.server_tls, self.server_cert, self.client_cert,
            self.client_meta["node_id"],
        )
        status, body = self._get(port, self.client_tls, self.server_cert)
        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["service"], "Node Core OS protected test page")
        self.assertEqual(payload["authenticated_node"], self.client_meta["node_id"])

    def test_untrusted_client_certificate_cannot_load_page(self):
        port = self._start_page(
            self.server_tls, self.server_cert, self.client_cert,
            self.client_meta["node_id"],
        )
        # The attacker trusts the legitimate server but presents a different node key.
        with self.assertRaises((OSError, http.client.HTTPException, ssl.SSLError)):
            self._get(port, self.attacker_tls, self.server_cert)

    def test_client_rejects_lookalike_web_server_certificate(self):
        # The fake page trusts the genuine client so only the server identity differs.
        port = self._start_page(
            self.attacker_tls, self.attacker_cert, self.client_cert,
            self.client_meta["node_id"],
        )
        # Client pins the real server certificate, not the impostor's certificate.
        with self.assertRaises((OSError, http.client.HTTPException, ssl.SSLError)):
            self._get(port, self.client_tls, self.server_cert)


if __name__ == "__main__":
    unittest.main()
