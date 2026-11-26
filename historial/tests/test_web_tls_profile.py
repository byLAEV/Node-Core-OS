"""Tests for the Node Core OS web TLS binding profile using synthetic certificates only."""
from datetime import datetime, timedelta, timezone
import tempfile
import unittest
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from node_core.identity.node_identity import NodeIdentityStore
from node_core.identity.web_tls_profile import (
    WebTLSProfileError,
    create_web_certificate_binding,
    verify_web_certificate_binding,
)


class WebTLSProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = NodeIdentityStore(Path(self.temp.name) / "node")
        self.store.initialize()
        self.now = datetime.now(timezone.utc)
        self.cert_key = Ed25519PrivateKey.generate()
        self.cert_pem = self._make_certificate()

    def _make_certificate(self, *, dns="example.test", before=None, after=None, server_auth=True, san=True):
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, dns)])
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(self.cert_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(before or self.now - timedelta(days=1))
            .not_valid_after(after or self.now + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        )
        if san:
            builder = builder.add_extension(x509.SubjectAlternativeName([x509.DNSName(dns)]), critical=False)
        if server_auth:
            builder = builder.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=None, decipher_only=None,
            ),
            critical=True,
        )
        return builder.sign(self.cert_key, algorithm=None).public_bytes(serialization.Encoding.PEM)

    def test_valid_web_certificate_can_be_bound_to_node(self):
        binding = create_web_certificate_binding(self.store, self.cert_pem, "example.test", now=self.now)
        self.assertTrue(verify_web_certificate_binding(binding, self.cert_pem, "example.test", now=self.now))

    def test_modified_binding_signature_is_rejected(self):
        binding = create_web_certificate_binding(self.store, self.cert_pem, "example.test", now=self.now)
        binding["dns_name"] = "attacker.test"
        self.assertFalse(verify_web_certificate_binding(binding, self.cert_pem, "example.test", now=self.now))

    def test_certificate_fingerprint_mismatch_is_rejected(self):
        binding = create_web_certificate_binding(self.store, self.cert_pem, "example.test", now=self.now)
        other_cert = self._make_certificate(dns="example.test")
        self.assertFalse(verify_web_certificate_binding(binding, other_cert, "example.test", now=self.now))

    def test_wrong_dns_name_is_rejected(self):
        with self.assertRaises(WebTLSProfileError):
            create_web_certificate_binding(self.store, self.cert_pem, "attacker.test", now=self.now)

    def test_expired_web_certificate_is_rejected(self):
        expired = self._make_certificate(
            before=self.now - timedelta(days=10),
            after=self.now - timedelta(days=1),
        )
        with self.assertRaises(WebTLSProfileError):
            create_web_certificate_binding(self.store, expired, "example.test", now=self.now)

    def test_missing_server_auth_eku_is_rejected(self):
        no_eku = self._make_certificate(server_auth=False)
        with self.assertRaises(WebTLSProfileError):
            create_web_certificate_binding(self.store, no_eku, "example.test", now=self.now)

    def test_missing_san_is_rejected(self):
        no_san = self._make_certificate(san=False)
        with self.assertRaises(WebTLSProfileError):
            create_web_certificate_binding(self.store, no_san, "example.test", now=self.now)


if __name__ == "__main__":
    unittest.main()
