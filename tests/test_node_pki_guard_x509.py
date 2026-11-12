import unittest
from datetime import datetime, timedelta
import shutil

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

from node_core.security.node_pki_guard_x509 import (
    OpenSSLVerificationError,
    X509ValidationPolicy,
    validate_x509_certificate,
)


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL executable is required")
class OpenSSLX509Tests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.utcnow()
        self.ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "NODE-PKI-GUARD Test CA")])
        self.ca = (
            x509.CertificateBuilder()
            .subject_name(self.ca_name)
            .issuer_name(self.ca_name)
            .public_key(self.ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(self.now - timedelta(days=1))
            .not_valid_after(self.now + timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(self.ca_key.public_key()), critical=False)
            .add_extension(x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=True,
                crl_sign=True, encipher_only=None, decipher_only=None,
            ), critical=True)
            .sign(self.ca_key, hashes.SHA256())
        )
        self.ca_pem = self.ca.public_bytes(serialization.Encoding.PEM)
        self.leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        leaf_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "service.example.test")])
        self.leaf = (
            x509.CertificateBuilder()
            .subject_name(leaf_name)
            .issuer_name(self.ca_name)
            .public_key(self.leaf_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(self.now - timedelta(minutes=1))
            .not_valid_after(self.now + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(self.ca_key.public_key()), critical=False)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(self.leaf_key.public_key()), critical=False)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("service.example.test")]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .add_extension(x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=True,
                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=None, decipher_only=None,
            ), critical=True)
            .sign(self.ca_key, hashes.SHA256())
        )
        self.leaf_pem = self.leaf.public_bytes(serialization.Encoding.PEM)

    def policy(self, hostname="service.example.test", ca=None):
        return X509ValidationPolicy(
            ca_bundle_pem=ca or self.ca_pem,
            purpose="sslserver",
            expected_hostname=hostname,
        )

    def test_valid_chain_and_hostname(self):
        result = validate_x509_certificate(self.leaf_pem, policy=self.policy())
        self.assertTrue(result.validated)
        self.assertEqual(result.identity_checked, "service.example.test")
        self.assertEqual(len(result.certificate_fingerprint_sha256), 64)
        self.assertEqual(len(result.spki_sha256), 64)
        self.assertFalse(result.revocation_checked)

    def test_wrong_hostname_rejected(self):
        with self.assertRaises(OpenSSLVerificationError):
            validate_x509_certificate(self.leaf_pem, policy=self.policy("attacker.example.test"))

    def test_untrusted_ca_rejected(self):
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        other_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Untrusted CA")])
        other_ca = (
            x509.CertificateBuilder().subject_name(other_name).issuer_name(other_name)
            .public_key(other_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(self.now - timedelta(days=1))
            .not_valid_after(self.now + timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(other_key, hashes.SHA256())
        )
        other_pem = other_ca.public_bytes(serialization.Encoding.PEM)
        with self.assertRaises(OpenSSLVerificationError):
            validate_x509_certificate(self.leaf_pem, policy=self.policy(ca=other_pem))

    def test_revocation_required_without_crl_rejected(self):
        with self.assertRaises(ValueError):
            X509ValidationPolicy(
                ca_bundle_pem=self.ca_pem, purpose="sslserver",
                expected_hostname="service.example.test", require_crl=True,
            )

    def test_exactly_one_peer_identity_required(self):
        with self.assertRaises(ValueError):
            X509ValidationPolicy(
                ca_bundle_pem=self.ca_pem, purpose="sslserver",
            )

    def test_client_certificate_purpose_rejected_for_server_leaf(self):
        policy = X509ValidationPolicy(
            ca_bundle_pem=self.ca_pem, purpose="sslclient",
            expected_hostname="service.example.test",
        )
        with self.assertRaises(OpenSSLVerificationError):
            validate_x509_certificate(self.leaf_pem, policy=policy)


if __name__ == "__main__":
    unittest.main()
