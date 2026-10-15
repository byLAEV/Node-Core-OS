import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.authentication import PeerAuthenticationError, PeerAuthenticator


class PeerAuthenticatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.node_a = NodeIdentityStore(root / "a")
        self.node_b = NodeIdentityStore(root / "b")
        self.node_a.initialize()
        self.node_b.initialize()
        self.hello_a = PeerAuthenticator.create_hello(self.node_a)
        self.hello_b = PeerAuthenticator.create_hello(self.node_b)

    def test_mutual_authentication_succeeds(self):
        auth_a = PeerAuthenticator.create_auth(
            self.node_a, self.hello_a, self.hello_b, "initiator"
        )
        auth_b = PeerAuthenticator.create_auth(
            self.node_b, self.hello_b, self.hello_a, "responder"
        )
        verified_a = PeerAuthenticator.verify_auth(
            auth_a, self.hello_a, self.hello_b, "responder"
        )
        verified_b = PeerAuthenticator.verify_auth(
            auth_b, self.hello_b, self.hello_a, "initiator"
        )
        self.assertEqual(verified_a["node_id"], self.hello_a["node_id"])
        self.assertEqual(verified_b["node_id"], self.hello_b["node_id"])

    def test_rejects_tampered_signature(self):
        auth_a = PeerAuthenticator.create_auth(
            self.node_a, self.hello_a, self.hello_b, "initiator"
        )
        auth_a["signature"] = "00" * 64
        with self.assertRaises(PeerAuthenticationError):
            PeerAuthenticator.verify_auth(
                auth_a, self.hello_a, self.hello_b, "responder"
            )

    def test_rejects_tampered_transcript(self):
        auth_a = PeerAuthenticator.create_auth(
            self.node_a, self.hello_a, self.hello_b, "initiator"
        )
        changed_hello_b = dict(self.hello_b)
        changed_hello_b["nonce"] = "11" * 32
        with self.assertRaises(PeerAuthenticationError):
            PeerAuthenticator.verify_auth(
                auth_a, self.hello_a, changed_hello_b, "responder"
            )

    def test_rejects_identity_substitution_in_auth(self):
        auth_a = PeerAuthenticator.create_auth(
            self.node_a, self.hello_a, self.hello_b, "initiator"
        )
        auth_a["node_id"] = self.hello_b["node_id"]
        auth_a["public_key"] = self.hello_b["public_key"]
        with self.assertRaises(PeerAuthenticationError):
            PeerAuthenticator.verify_auth(
                auth_a, self.hello_a, self.hello_b, "responder"
            )

    def test_rejects_malformed_hello_and_bad_node_id(self):
        malformed = dict(self.hello_a)
        malformed["node_id"] = "sha256:" + "0" * 64
        with self.assertRaises(PeerAuthenticationError):
            PeerAuthenticator.create_auth(
                self.node_a, malformed, self.hello_b, "initiator"
            )

    def test_rejects_same_node_identity(self):
        hello_a2 = PeerAuthenticator.create_hello(self.node_a)
        with self.assertRaises(PeerAuthenticationError):
            PeerAuthenticator.create_auth(
                self.node_a, self.hello_a, hello_a2, "initiator"
            )

    def test_rejects_invalid_role(self):
        with self.assertRaises(PeerAuthenticationError):
            PeerAuthenticator.create_auth(
                self.node_a, self.hello_a, self.hello_b, "unknown"
            )

    def test_rejects_replay_against_fresh_hello(self):
        old_auth = PeerAuthenticator.create_auth(
            self.node_a, self.hello_a, self.hello_b, "initiator"
        )
        fresh_hello_b = PeerAuthenticator.create_hello(self.node_b)
        with self.assertRaises(PeerAuthenticationError):
            PeerAuthenticator.verify_auth(
                old_auth, self.hello_a, fresh_hello_b, "responder"
            )


if __name__ == "__main__":
    unittest.main()
