"""Real loopback HTTPS tests using standard CA-chain and hostname validation.

All CA and server keys are synthetic. The server binds only to loopback. No public
hosts, production certificates, or external devices are contacted.
"""
from datetime import datetime, timedelta, timezone
import http.client
import ssl
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def _build_ca(now):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Node Core OS test CA")])
    cert = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before((now - timedelta(days=2)).replace(tzinfo=None))
        .not_valid_after((now + timedelta(days=30)).replace(tzinfo=None))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=False, key_encipherment=False,
            data_encipherment=False, key_agreement=False, key_cert_sign=True,
            crl_sign=True, encipher_only=None, decipher_only=None,
        ), critical=True)
        .sign(key, hashes.SHA256())
    )
    return key, cert


def _build_leaf(ca_key, ca_cert, now, *, dns="localhost", not_before=None):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, dns)])
    cert = (
        x509.CertificateBuilder().subject_name(subject).issuer_name(ca_cert.subject)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before((not_before or (now - timedelta(minutes=5))).replace(tzinfo=None))
        .not_valid_after((now + timedelta(days=7)).replace(tzinfo=None))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(dns)]), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=False, key_encipherment=True,
            data_encipherment=False, key_agreement=False, key_cert_sign=False,
            crl_sign=False, encipher_only=None, decipher_only=None,
        ), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    return key, cert


def _write_pem_pair(folder, key, cert):
    cert_path = Path(folder) / "server.pem"
    key_path = Path(folder) / "server-key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    return cert_path, key_path


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"node-core-os-test-ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


class _LoopbackServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class _FixedAddressHTTPSConnection(http.client.HTTPSConnection):
    """Connect to loopback while retaining a caller-selected TLS server_hostname."""
    def connect(self):
        raw = socket.create_connection(("127.0.0.1", self.port), timeout=self.timeout)
        self.sock = self._context.wrap_socket(raw, server_hostname=self.host)


class StandardHTTPSValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = datetime.now(timezone.utc)
        self.ca_key, self.ca_cert = _build_ca(self.now)
        self.ca_pem = self.ca_cert.public_bytes(serialization.Encoding.PEM)
        self.server = None
        self.thread = None

    def tearDown(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=3)
        self.temp.cleanup()

    def _start_server(self, *, dns="localhost", not_before=None, signed_by=None):
        ca_key, ca_cert = signed_by or (self.ca_key, self.ca_cert)
        key, cert = _build_leaf(ca_key, ca_cert, self.now, dns=dns, not_before=not_before)
        cert_path, key_path = _write_pem_pair(self.temp.name, key, cert)
        server = _LoopbackServer(("127.0.0.1", 0), _Handler)
        server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        server_ctx.load_cert_chain(str(cert_path), str(key_path))
        server.socket = server_ctx.wrap_socket(server.socket, server_side=True)
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)
        self.thread.start()
        return server.server_address[1]

    def _client_context(self, ca_pem=None):
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.load_verify_locations(cadata=(ca_pem or self.ca_pem).decode("ascii"))
        return ctx

    def test_valid_ca_chain_and_hostname_are_accepted(self):
        port = self._start_server()
        conn = _FixedAddressHTTPSConnection("localhost", port, context=self._client_context(), timeout=3)
        try:
            conn.request("GET", "/health")
            response = conn.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"node-core-os-test-ok")
        finally:
            conn.close()

    def test_wrong_hostname_is_rejected_during_real_tls_handshake(self):
        port = self._start_server(dns="localhost")
        conn = _FixedAddressHTTPSConnection("wrong.example.test", port, context=self._client_context(), timeout=3)
        try:
            with self.assertRaises(ssl.SSLCertVerificationError):
                conn.request("GET", "/health")
        finally:
            conn.close()

    def test_not_yet_valid_certificate_is_rejected_during_real_tls_handshake(self):
        port = self._start_server(not_before=self.now + timedelta(days=1))
        conn = _FixedAddressHTTPSConnection("localhost", port, context=self._client_context(), timeout=3)
        try:
            with self.assertRaises(ssl.SSLCertVerificationError):
                conn.request("GET", "/health")
        finally:
            conn.close()

    def test_untrusted_ca_is_rejected_during_real_tls_handshake(self):
        other_ca_key, other_ca_cert = _build_ca(self.now)
        port = self._start_server(signed_by=(other_ca_key, other_ca_cert))
        conn = _FixedAddressHTTPSConnection("localhost", port, context=self._client_context(), timeout=3)
        try:
            with self.assertRaises(ssl.SSLCertVerificationError):
                conn.request("GET", "/health")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
