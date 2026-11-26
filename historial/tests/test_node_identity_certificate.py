from datetime import datetime, timedelta, timezone
import base64
import json
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from node_core.security.node_identity_certificate import (
    NodeCertificateError, issue_certificate, verify_certificate,
)


def public_bytes(key):
    return key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


class NodeIdentityCertificateTests(unittest.TestCase):
    def setUp(self):
        self.issuer = Ed25519PrivateKey.generate()
        self.subject = Ed25519PrivateKey.generate()
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.token = issue_certificate(
            issuer_id="did:nodecore:issuer-01",
            issuer_key_id="issuer-key-01",
            issuer_private_key=self.issuer,
            node_id="node-01",
            node_public_key_hex=public_bytes(self.subject.public_key()).hex(),
            profile="identity-key-protection",
            issued_at=self.now,
            expires_at=self.now + timedelta(days=30),
        )
        self.trust = {"issuer-key-01": public_bytes(self.issuer.public_key())}

    def test_valid_certificate(self):
        claims = verify_certificate(self.token, trusted_issuers=self.trust, trusted_issuer_ids={"issuer-key-01": "did:nodecore:issuer-01"}, now=self.now)
        self.assertEqual(claims["sub"], "node-01")
        self.assertEqual(claims["node_core"]["profile"], "identity-key-protection")

    def test_tampered_payload_rejected(self):
        parts = self.token.split(".")
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
        payload["sub"] = "attacker"
        parts[1] = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        with self.assertRaises(NodeCertificateError):
            verify_certificate(".".join(parts), trusted_issuers=self.trust, trusted_issuer_ids={"issuer-key-01": "did:nodecore:issuer-01"}, now=self.now)

    def test_unknown_issuer_rejected(self):
        with self.assertRaises(NodeCertificateError):
            verify_certificate(self.token, trusted_issuers={}, trusted_issuer_ids={}, now=self.now)

    def test_trusted_key_cannot_assert_a_different_issuer_identity(self):
        forged_identity_token = issue_certificate(
            issuer_id="did:nodecore:attacker",
            issuer_key_id="issuer-key-01",
            issuer_private_key=self.issuer,
            node_id="node-01",
            node_public_key_hex=public_bytes(self.subject.public_key()).hex(),
            profile="identity-key-protection",
            issued_at=self.now,
            expires_at=self.now + timedelta(days=30),
        )
        with self.assertRaisesRegex(NodeCertificateError, "Issuer identity"):
            verify_certificate(
                forged_identity_token,
                trusted_issuers=self.trust,
                trusted_issuer_ids={"issuer-key-01": "did:nodecore:issuer-01"},
                now=self.now,
            )

    def test_missing_trusted_issuer_identity_fails_closed(self):
        with self.assertRaisesRegex(NodeCertificateError, "identity is missing"):
            verify_certificate(
                self.token,
                trusted_issuers=self.trust,
                trusted_issuer_ids={},
                now=self.now,
            )

    def test_revoked_certificate_rejected(self):
        claims = verify_certificate(self.token, trusted_issuers=self.trust, trusted_issuer_ids={"issuer-key-01": "did:nodecore:issuer-01"}, now=self.now)
        with self.assertRaises(NodeCertificateError):
            verify_certificate(self.token, trusted_issuers=self.trust, trusted_issuer_ids={"issuer-key-01": "did:nodecore:issuer-01"}, now=self.now,
                               revoked_ids={claims["jti"]})

    def test_expired_certificate_rejected(self):
        with self.assertRaises(NodeCertificateError):
            verify_certificate(self.token, trusted_issuers=self.trust,
                               trusted_issuer_ids={"issuer-key-01": "did:nodecore:issuer-01"},
                               now=self.now + timedelta(days=31))

    def test_long_lifetime_rejected_at_issuance(self):
        with self.assertRaises(NodeCertificateError):
            issue_certificate(
                issuer_id="issuer", issuer_key_id="kid", issuer_private_key=self.issuer,
                node_id="node", node_public_key_hex=public_bytes(self.subject.public_key()).hex(),
                profile="identity-key-protection", issued_at=self.now,
                expires_at=self.now + timedelta(days=91),
            )

    def test_unsupported_profile_rejected(self):
        with self.assertRaises(NodeCertificateError):
            issue_certificate(
                issuer_id="issuer", issuer_key_id="kid", issuer_private_key=self.issuer,
                node_id="node", node_public_key_hex=public_bytes(self.subject.public_key()).hex(),
                profile="admin-everything", issued_at=self.now,
                expires_at=self.now + timedelta(days=2),
            )


if __name__ == "__main__":
    unittest.main()
