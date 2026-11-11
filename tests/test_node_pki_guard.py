import base64
import unittest
from datetime import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.x509.oid import NameOID

from node_core.security.node_pki_guard import (
    AUTH_FORMAT, BINDING_FORMAT, POP_DOMAIN, PROTOCOL_VERSION,
    ChallengeRegistry, NodePKIGuardError, ReplayError, canonical_json,
    certificate_fingerprints, evaluate_authorization, operation_digest,
    sign_challenge, verify_dual_proof,
)


def b64u(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class FakeUTXOView:
    def __init__(self, records):
        self.records = records

    def get_unspent_authorization(self, outpoint):
        return self.records.get(outpoint)


class NodePKIGuardTests(unittest.TestCase):
    def setUp(self):
        self.node_key = ed25519.Ed25519PrivateKey.generate()
        self.x509_key = ec.generate_private_key(ec.SECP256R1())
        self.now = 1800000000
        self.challenge = {
            "domain": POP_DOMAIN, "version": PROTOCOL_VERSION,
            "challenge_id": "challenge-001", "nonce": b64u(b"N" * 32),
            "node_id": "node-test-01", "x509_fingerprint_sha256": "a" * 64,
            "spki_sha256": "b" * 64, "purpose": "TLS_CLIENT_AUTH",
            "audience": "api.example.test", "operation_hash": "c" * 64,
            "issued_at": self.now - 5, "expires_at": self.now + 300,
        }

    def test_canonical_json_is_deterministic(self):
        self.assertEqual(canonical_json({"z": 1, "a": "é"}), '{"a":"é","z":1}'.encode())

    def test_canonical_json_rejects_float(self):
        with self.assertRaises(NodePKIGuardError):
            canonical_json({"unsafe": 1.25})

    def test_valid_dual_proof(self):
        digest = verify_dual_proof(
            challenge=self.challenge, node_public_key=self.node_key.public_key(),
            x509_public_key=self.x509_key.public_key(),
            node_signature=sign_challenge(self.node_key, self.challenge),
            x509_signature=sign_challenge(self.x509_key, self.challenge),
            registry=ChallengeRegistry(), now_epoch=self.now)
        self.assertEqual(len(digest), 64)

    def test_invalid_node_signature_rejected(self):
        other = ed25519.Ed25519PrivateKey.generate()
        with self.assertRaises(NodePKIGuardError):
            verify_dual_proof(
                challenge=self.challenge, node_public_key=self.node_key.public_key(),
                x509_public_key=self.x509_key.public_key(),
                node_signature=sign_challenge(other, self.challenge),
                x509_signature=sign_challenge(self.x509_key, self.challenge),
                registry=ChallengeRegistry(), now_epoch=self.now)

    def test_invalid_x509_signature_rejected(self):
        other = ec.generate_private_key(ec.SECP256R1())
        with self.assertRaises(NodePKIGuardError):
            verify_dual_proof(
                challenge=self.challenge, node_public_key=self.node_key.public_key(),
                x509_public_key=self.x509_key.public_key(),
                node_signature=sign_challenge(self.node_key, self.challenge),
                x509_signature=sign_challenge(other, self.challenge),
                registry=ChallengeRegistry(), now_epoch=self.now)

    def test_challenge_replay_rejected(self):
        registry = ChallengeRegistry()
        args = dict(
            challenge=self.challenge, node_public_key=self.node_key.public_key(),
            x509_public_key=self.x509_key.public_key(),
            node_signature=sign_challenge(self.node_key, self.challenge),
            x509_signature=sign_challenge(self.x509_key, self.challenge),
            registry=registry, now_epoch=self.now)
        verify_dual_proof(**args)
        with self.assertRaises(ReplayError):
            verify_dual_proof(**args)

    def test_expired_challenge_rejected(self):
        challenge = dict(self.challenge, expires_at=self.now - 1)
        with self.assertRaises(NodePKIGuardError):
            verify_dual_proof(
                challenge=challenge, node_public_key=self.node_key.public_key(),
                x509_public_key=self.x509_key.public_key(),
                node_signature=sign_challenge(self.node_key, challenge),
                x509_signature=sign_challenge(self.x509_key, challenge),
                registry=ChallengeRegistry(), now_epoch=self.now)

    def test_rsa_pop_supported(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        challenge = dict(self.challenge, challenge_id="rsa-challenge")
        verify_dual_proof(
            challenge=challenge, node_public_key=self.node_key.public_key(),
            x509_public_key=key.public_key(),
            node_signature=sign_challenge(self.node_key, challenge),
            x509_signature=sign_challenge(key, challenge),
            registry=ChallengeRegistry(), now_epoch=self.now)

    def test_x509_fingerprints_from_generated_certificate(self):
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test.example")])
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                .public_key(self.x509_key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(datetime(2026, 1, 1)).not_valid_after(datetime(2027, 1, 1))
                .sign(self.x509_key, hashes.SHA256()))
        pem = cert.public_bytes(serialization.Encoding.PEM)
        cert_fp, spki_fp = certificate_fingerprints(pem)
        self.assertEqual(cert_fp, cert.fingerprint(hashes.SHA256()).hex())
        self.assertEqual(len(spki_fp), 64)

    def fixtures(self):
        context = {"node_id": "node-test-01", "operation": "SOFTWARE_RELEASE_SIGNING",
                   "audience": "release.example.test", "artifact_sha256": "d" * 64}
        op_hash = operation_digest(context)
        binding = {
            "format": BINDING_FORMAT, "version": PROTOCOL_VERSION,
            "binding_id": "binding-01", "node_id": "node-test-01",
            "x509_fingerprint_sha256": "a" * 64, "spki_sha256": "b" * 64,
            "purpose": "CODE_SIGNING", "allowed_operations": ["SOFTWARE_RELEASE_SIGNING"],
            "denied_operations": [], "constraints": {}, "issuer_key_id": "binding-issuer",
            "issued_at": self.now - 100, "expires_at": self.now + 500,
            "binding_status": "ACTIVE",
            "proof_of_possession": {"challenge_id": "challenge-01", "challenge_hash": "e" * 64,
                                    "node_signature": "sig-node", "x509_signature": "sig-x509",
                                    "verified_at": self.now - 90}}
        auth = {
            "format": AUTH_FORMAT, "version": PROTOCOL_VERSION,
            "authorization_id": "auth-01", "outpoint": "f" * 64 + ":0",
            "binding_id": "binding-01", "node_id": "node-test-01",
            "operation": "SOFTWARE_RELEASE_SIGNING", "operation_hash": op_hash,
            "audience": "release.example.test", "policy_id": "release-policy",
            "policy_version": "1", "context_hash": "e" * 64,
            "valid_from_epoch": 100, "valid_until_epoch": 200,
            "required_signatures": [{"key_id": "node-01", "algorithm": "Ed25519"}],
            "single_use": True}
        return context, binding, auth

    def evaluate(self, context, binding, auth, view, **overrides):
        args = dict(mode="PROTECTED", operation_context=context, binding=binding,
                    authorization=auth, utxo_view=view, now_epoch=self.now,
                    current_epoch=120, x509_validated=True, dual_proof_verified=True)
        args.update(overrides)
        return evaluate_authorization(**args)

    def test_standard_path_does_not_consume_utxo(self):
        decision = evaluate_authorization(
            mode="STANDARD", operation_context={"node_id": "n", "operation": "READ"},
            binding=None, authorization=None, utxo_view=None, now_epoch=self.now,
            current_epoch=120, x509_validated=True, dual_proof_verified=False)
        self.assertEqual(decision.decision, "STANDARD")

    def test_deny_policy_rejects(self):
        decision = evaluate_authorization(
            mode="DENY", operation_context={}, binding=None, authorization=None,
            utxo_view=None, now_epoch=self.now, current_epoch=120,
            x509_validated=True, dual_proof_verified=True)
        self.assertEqual(decision.decision, "DENY")

    def test_protected_accepts_matching_unspent_utxo(self):
        context, binding, auth = self.fixtures()
        decision = self.evaluate(context, binding, auth, FakeUTXOView({auth["outpoint"]: auth}))
        self.assertEqual(decision.decision, "PROTECTED")
        self.assertIn("consensus finality", decision.reason)

    def test_protected_fails_without_x509(self):
        context, binding, auth = self.fixtures()
        self.assertEqual(self.evaluate(context, binding, auth,
                         FakeUTXOView({auth["outpoint"]: auth}), x509_validated=False).decision, "DENY")

    def test_protected_fails_without_dual_proof(self):
        context, binding, auth = self.fixtures()
        self.assertEqual(self.evaluate(context, binding, auth,
                         FakeUTXOView({auth["outpoint"]: auth}), dual_proof_verified=False).decision, "DENY")

    def test_protected_fails_when_utxo_missing_or_spent(self):
        context, binding, auth = self.fixtures()
        decision = self.evaluate(context, binding, auth, FakeUTXOView({}))
        self.assertEqual(decision.decision, "DENY")
        self.assertIn("missing or already spent", decision.reason)

    def test_protected_fails_on_operation_tampering(self):
        context, binding, auth = self.fixtures()
        altered = dict(context, artifact_sha256="0" * 64)
        decision = self.evaluate(altered, binding, auth, FakeUTXOView({auth["outpoint"]: auth}))
        self.assertEqual(decision.decision, "DENY")
        self.assertIn("hash mismatch", decision.reason)

    def test_protected_fails_on_binding_denial(self):
        context, binding, auth = self.fixtures()
        binding["denied_operations"] = ["SOFTWARE_RELEASE_SIGNING"]
        self.assertEqual(self.evaluate(context, binding, auth,
                         FakeUTXOView({auth["outpoint"]: auth})).decision, "DENY")

    def test_protected_fails_outside_epoch(self):
        context, binding, auth = self.fixtures()
        self.assertEqual(self.evaluate(context, binding, auth,
                         FakeUTXOView({auth["outpoint"]: auth}), current_epoch=201).decision, "DENY")


if __name__ == "__main__":
    unittest.main()
