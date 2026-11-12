import ipaddress
import unittest
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from cryptography.x509.oid import NameOID

from node_core.security.node_pki_guard_issuer import (
    CSRValidationError,
    IssuerConfigurationError,
    X509IssuanceProfile,
    issue_x509_certificate,
)


class X509IssuerTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
        self.ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.ca_name = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NODE Core OS Test"),
            x509.NameAttribute(NameOID.COMMON_NAME, "NODE-PKI-GUARD Test Root"),
        ])
        self.ca = (
            x509.CertificateBuilder()
            .subject_name(self.ca_name)
            .issuer_name(self.ca_name)
            .public_key(self.ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before((self.now - timedelta(days=1)).replace(tzinfo=None))
            .not_valid_after((self.now + timedelta(days=365)).replace(tzinfo=None))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(self.ca_key.public_key()), critical=False)
            .add_extension(x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=True,
                crl_sign=True, encipher_only=None, decipher_only=None,
            ), critical=True)
            .sign(self.ca_key, hashes.SHA256())
        )
        self.ca_pem = self.ca.public_bytes(serialization.Encoding.PEM)
        self.ca_key_pem = self.ca_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        self.ca_fingerprint = self.ca.fingerprint(hashes.SHA256()).hex()
        self.leaf_key = ec.generate_private_key(ec.SECP256R1())
        self.profile = X509IssuanceProfile(
            profile_id="NODE-TLS-SERVER",
            profile_version="1.0",
            allowed_dns_suffixes=("example.test",),
            validity_days=30,
        )

    def make_csr(self, *, san="api.example.test", extra_extension=None, key=None):
        private_key = key or self.leaf_key
        builder = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, san),
        ]))
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(san)]), critical=False
        )
        if extra_extension is not None:
            builder = builder.add_extension(extra_extension, critical=False)
        csr = builder.sign(private_key, hashes.SHA256())
        return csr.public_bytes(serialization.Encoding.PEM)

    def issue(self, **overrides):
        args = dict(
            csr_pem=self.make_csr(),
            issuer_certificate_pem=self.ca_pem,
            issuer_private_key_pem=self.ca_key_pem,
            trusted_issuer_fingerprint_sha256=self.ca_fingerprint,
            profile=self.profile,
            now_utc=self.now,
        )
        args.update(overrides)
        return issue_x509_certificate(**args)

    def test_issue_valid_leaf_certificate(self):
        result = self.issue()
        cert = x509.load_pem_x509_certificate(result.certificate_pem)
        self.assertEqual(cert.subject, x509.load_pem_x509_csr(self.make_csr()).subject)
        self.assertEqual(cert.issuer, self.ca.subject)
        self.assertEqual(cert.public_key().public_numbers(), self.leaf_key.public_key().public_numbers())
        self.assertFalse(cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca)
        self.assertEqual(
            cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName),
            ["api.example.test"],
        )
        self.assertEqual(result.issuer_fingerprint_sha256, self.ca_fingerprint)
        self.assertEqual(result.profile_id, "NODE-TLS-SERVER")
        self.assertEqual(len(result.certificate_fingerprint_sha256), 64)
        self.assertEqual(len(result.spki_sha256), 64)
        self.assertLessEqual(
            cert.not_valid_after_utc,
            self.ca.not_valid_after_utc,
        )

    def test_certificate_signature_verifies_with_ca_public_key(self):
        result = self.issue()
        cert = x509.load_pem_x509_certificate(result.certificate_pem)
        self.ca_key.public_key().verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            cert.signature_hash_algorithm,
        )

    def test_wrong_ca_fingerprint_pin_rejected(self):
        with self.assertRaises(IssuerConfigurationError):
            self.issue(trusted_issuer_fingerprint_sha256="0" * 64)

    def test_mismatched_ca_private_key_rejected(self):
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        other_pem = other.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        with self.assertRaises(IssuerConfigurationError):
            self.issue(issuer_private_key_pem=other_pem)

    def test_non_ca_certificate_rejected(self):
        leaf = (
            x509.CertificateBuilder()
            .subject_name(self.ca_name)
            .issuer_name(self.ca_name)
            .public_key(self.ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before((self.now - timedelta(days=1)).replace(tzinfo=None))
            .not_valid_after((self.now + timedelta(days=30)).replace(tzinfo=None))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=True,
                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=None, decipher_only=None,
            ), critical=True)
            .sign(self.ca_key, hashes.SHA256())
        )
        pem = leaf.public_bytes(serialization.Encoding.PEM)
        with self.assertRaises(IssuerConfigurationError):
            self.issue(issuer_certificate_pem=pem,
                       trusted_issuer_fingerprint_sha256=leaf.fingerprint(hashes.SHA256()).hex())

    def test_expired_ca_rejected(self):
        expired = (
            x509.CertificateBuilder()
            .subject_name(self.ca_name)
            .issuer_name(self.ca_name)
            .public_key(self.ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before((self.now - timedelta(days=365)).replace(tzinfo=None))
            .not_valid_after((self.now - timedelta(days=1)).replace(tzinfo=None))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=True,
                crl_sign=True, encipher_only=None, decipher_only=None,
            ), critical=True)
            .sign(self.ca_key, hashes.SHA256())
        )
        pem = expired.public_bytes(serialization.Encoding.PEM)
        with self.assertRaises(IssuerConfigurationError):
            self.issue(issuer_certificate_pem=pem,
                       trusted_issuer_fingerprint_sha256=expired.fingerprint(hashes.SHA256()).hex())

    def test_csr_dns_outside_profile_rejected(self):
        with self.assertRaises(CSRValidationError):
            self.issue(csr_pem=self.make_csr(san="api.attacker.invalid"))

    def test_csr_wildcard_dns_rejected(self):
        with self.assertRaises(CSRValidationError):
            self.issue(csr_pem=self.make_csr(san="*.example.test"))

    def test_unapproved_csr_extension_rejected(self):
        with self.assertRaises(CSRValidationError):
            self.issue(csr_pem=self.make_csr(
                extra_extension=x509.BasicConstraints(ca=True, path_length=None)
            ))

    def test_ip_san_rejected_unless_profile_explicitly_allows_it(self):
        key = self.leaf_key
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "api.example.test")]))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("192.0.2.10"))]), critical=False)
            .sign(key, hashes.SHA256())
            .public_bytes(serialization.Encoding.PEM)
        )
        with self.assertRaises(CSRValidationError):
            self.issue(csr_pem=csr)
        profile = X509IssuanceProfile(
            profile_id="NODE-IP-SERVER",
            profile_version="1.0",
            allowed_dns_suffixes=(),
            allow_ip_sans=True,
        )
        result = self.issue(csr_pem=csr, profile=profile)
        cert = x509.load_pem_x509_certificate(result.certificate_pem)
        self.assertEqual(
            cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress)[0].compressed,
            "192.0.2.10",
        )

    def test_ed25519_leaf_csr_is_supported(self):
        key = ed25519.Ed25519PrivateKey.generate()
        result = self.issue(csr_pem=self.make_csr(key=key))
        cert = x509.load_pem_x509_certificate(result.certificate_pem)
        self.assertIsInstance(cert.public_key(), ed25519.Ed25519PublicKey)

    def test_ca_validity_caps_leaf_validity(self):
        short_profile = X509IssuanceProfile(
            profile_id="NODE-SHORT",
            profile_version="1.0",
            allowed_dns_suffixes=("example.test",),
            validity_days=397,
        )
        result = self.issue(profile=short_profile)
        cert = x509.load_pem_x509_certificate(result.certificate_pem)
        self.assertEqual(cert.not_valid_after_utc, self.ca.not_valid_after_utc)

    def test_naive_clock_rejected(self):
        with self.assertRaises(ValueError):
            self.issue(now_utc=datetime(2026, 11, 11, 12, 0))

    def test_profile_rejects_wildcard_allowlist(self):
        with self.assertRaises(ValueError):
            X509IssuanceProfile(
                profile_id="NODE-BAD",
                profile_version="1.0",
                allowed_dns_suffixes=("*.example.test",),
            )


if __name__ == "__main__":
    unittest.main()
