import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.identity_proof import (
    IdentityProofError,
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
        with self.assertRaises(IdentityProofError):
            create_response(self.node_b, {"nonce": "00"})
        with self.assertRaises(IdentityProofError):
            verify_response(
                {"type": "IDENTITY_CHALLENGE", "protocol_version": True,
                 "purpose": "wrong", "nonce": "00" * 32},
                {},
            )

    def test_replay_requires_a_new_challenge_and_fails(self):
        old_challenge = create_challenge()
        old_response = create_response(self.node_b, old_challenge)
        new_challenge = create_challenge()
        self.assertNotEqual(old_challenge["nonce"], new_challenge["nonce"])
        with self.assertRaises(IdentityProofError):
            verify_response(new_challenge, old_response)

    def test_identity_proof_is_bounded_and_does_not_require_kubo(self):
        challenge = create_challenge()
        response = create_response(self.node_b, challenge)
        self.assertLess(len(str(response).encode("utf-8")), 4096)
        self.assertEqual(verify_response(challenge, response)["authorization"], "none")


if __name__ == "__main__":
    unittest.main()
