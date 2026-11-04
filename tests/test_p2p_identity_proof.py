import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.identity_proof import (
    IdentityProofError,
    MAX_MESSAGE_BYTES,
    create_challenge,
    create_response,
    verify_response,
)


class LANIdentityProofTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.node_a = NodeIdentityStore(Path(self.temp.name) / "a")
        self.node_b = NodeIdentityStore(Path(self.temp.name) / "b")
        self.node_a.initialize()
        self.node_b.initialize()

    def test_fresh_challenge_proves_key_possession_without_trust(self):
        challenge = create_challenge()
        response = create_response(self.node_b, challenge)
        result = verify_response(challenge, response)
        self.assertEqual(result["node_id"], self.node_b.load()["node_id"])
        self.assertEqual(result["trust_status"], "not_trusted")
        self.assertEqual(result["authorization"], "none")
        self.assertEqual(result["session_established"], "false")

    def test_modified_challenge_invalidates_signature(self):
        challenge = create_challenge()
        response = create_response(self.node_b, challenge)
        modified = dict(challenge)
        modified["nonce"] = "11" * 32
        with self.assertRaises(IdentityProofError):
            verify_response(modified, response)

    def test_identity_substitution_is_rejected(self):
        challenge = create_challenge()
        response = create_response(self.node_b, challenge)
        response["node_id"] = self.node_a.load()["node_id"]
        with self.assertRaises(IdentityProofError):
            verify_response(challenge, response)

    def test_modified_signature_is_rejected(self):
        challenge = create_challenge()
        response = create_response(self.node_b, challenge)
        response["signature"] = "00" * 64
        with self.assertRaises(IdentityProofError):
            verify_response(challenge, response)

    def test_malformed_challenge_is_rejected(self):
        malformed = [
            {"nonce": "00"},
            {"type": "IDENTITY_CHALLENGE", "protocol_version": True,
             "purpose": "wrong", "nonce": "00" * 32},
            {"type": "IDENTITY_CHALLENGE", "protocol_version": 1,
             "purpose": "node-core-os/p2p-lan-identity-proof/v1", "nonce": "aa " * 32},
        ]
        for challenge in malformed:
            with self.subTest(challenge=challenge):
                with self.assertRaises(IdentityProofError):
                    create_response(self.node_b, challenge)

    def test_replay_requires_a_new_challenge_and_fails(self):
        old_challenge = create_challenge()
        old_response = create_response(self.node_b, old_challenge)
        new_challenge = create_challenge()
        self.assertNotEqual(old_challenge["nonce"], new_challenge["nonce"])
        with self.assertRaises(IdentityProofError):
            verify_response(new_challenge, old_response)

    def test_signature_and_public_fields_require_strict_lowercase_hex(self):
        challenge = create_challenge()
        response = create_response(self.node_b, challenge)
        for field, invalid in (
            ("public_key", "A" + response["public_key"][1:]),
            ("signature", response["signature"] + " " * 5),
            ("signature", "f" * (MAX_MESSAGE_BYTES * 2)),
        ):
            candidate = dict(response)
            candidate[field] = invalid
            with self.subTest(field=field, value_length=len(invalid)):
                with self.assertRaises(IdentityProofError):
                    verify_response(challenge, candidate)

    def test_identity_id_requires_canonical_sha256_hex(self):
        challenge = create_challenge()
        response = create_response(self.node_b, challenge)
        response["node_id"] = "sha256:" + "A" * 64
        with self.assertRaises(IdentityProofError):
            verify_response(challenge, response)

    def test_identity_proof_is_bounded_and_does_not_require_kubo(self):
        challenge = create_challenge()
        response = create_response(self.node_b, challenge)
        self.assertLess(len(str(response).encode("utf-8")), MAX_MESSAGE_BYTES)
        self.assertEqual(verify_response(challenge, response)["authorization"], "none")


if __name__ == "__main__":
    unittest.main()
