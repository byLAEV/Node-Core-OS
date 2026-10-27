"""Adversarial tests for Node Core OS certificate and identity validation.

These tests use temporary identities and synthetic certificates only. They never
contact external hosts or read real user identity material.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import tempfile
import unittest
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import NameOID

from node_core.identity.node_identity import NodeIdentityError, NodeIdentityStore
from node_core.p2p.tls_transport import NodeTLSTransport, TLSTransportError


class CertificateAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = NodeIdentityStore(self.root / "node")
        self.metadata = self.store.initialize()
        self.transport = NodeTLSTransport(self.store)
        self.good_pem = self.transport.ensure_certificate()

    def _private_key(self):
        return serialization.load_pem_private_key(
            self.store.private_key_path.read_bytes(), password=None
        )

    def _certificate(self, *, signing_key=None, not_before=None, not_after=None,
                     subject=None, issuer=None, add_san=True):
        key = self._private_key()
        now = datetime.now(timezone.utc)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "adversarial-test")])
        subject = subject or x509.load_pem_x509_certificate(self.good_pem).subject
        issuer = issuer or subject
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_before or now - timedelta(minutes=5))
            .not_valid_after(not_after or now + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        )
        if add_san:
            builder = builder.add_extension(
                x509.SubjectAlternativeName([
                    x509.UniformResourceIdentifier(
                        "urn:node-core-os:node:" + self.metadata["node_id"]
                    )
                ]),
                critical=False,
            )
        return builder.sign(signing_key or key, algorithm=None).public_bytes(
            serialization.Encoding.PEM
        )

    def test_valid_certificate_is_accepted_and_bound_to_node(self):
        cert = x509.load_pem_x509_certificate(self.good_pem)
        public_key = cert.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        self.assertEqual(public_key.hex(), self.metadata["public_key"])
        self.assertEqual(
            "sha256:" + hashlib.sha256(public_key).hexdigest(),
            self.metadata["node_id"],
        )
        self.assertEqual(self.transport.ensure_certificate(), self.good_pem)

    def test_certificate_from_another_node_is_rejected(self):
        other_store = NodeIdentityStore(self.root / "other")
        other_store.initialize()
        other_pem = NodeTLSTransport(other_store).ensure_certificate()
        self.store.identity_dir.joinpath("node-cert.pem").write_bytes(other_pem)
        with self.assertRaises(TLSTransportError):
            self.transport.ensure_certificate()

    def test_corrupted_pem_is_rejected(self):
        self.transport.certificate_path.write_bytes(b"-----BEGIN CERTIFICATE-----\nnot-a-certificate")
        with self.assertRaises(TLSTransportError):
            self.transport.ensure_certificate()

    def test_tampered_identity_metadata_is_rejected(self):
        original = self.store.metadata_path.read_text(encoding="utf-8")
        self.store.metadata_path.write_text(
            original.replace(self.metadata["node_id"], "sha256:" + "0" * 64),
            encoding="utf-8",
        )
        with self.assertRaises(NodeIdentityError):
            self.store.load()

    def test_tampered_signature_is_rejected(self):
        message = b"node-core-os certificate security test"
        signature = self.store.sign(message)
        self.assertTrue(NodeIdentityStore.verify(self.metadata["public_key"], message, signature))
        self.assertFalse(
            NodeIdentityStore.verify(self.metadata["public_key"], message + b"!", signature)
        )

    def test_expired_certificate_is_rejected(self):
        now = datetime.now(timezone.utc)
        expired_pem = self._certificate(
            not_before=now - timedelta(days=20),
            not_after=now - timedelta(days=10),
        )
        self.transport.certificate_path.write_bytes(expired_pem)
        with self.assertRaises(TLSTransportError):
            self.transport.ensure_certificate()

    def test_certificate_with_invalid_self_signature_is_rejected(self):
        attacker_key = Ed25519PrivateKey.generate()
        invalidly_signed_pem = self._certificate(signing_key=attacker_key)
        self.transport.certificate_path.write_bytes(invalidly_signed_pem)
        with self.assertRaises(TLSTransportError):
            self.transport.ensure_certificate()


if __name__ == "__main__":
    unittest.main()
