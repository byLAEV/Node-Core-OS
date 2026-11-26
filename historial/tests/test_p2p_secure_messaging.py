import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.secure_messaging import (
    NodeRSAIdentityStore,
    SecureMessagingError,
    create_ack,
    open_message,
    seal_message,
    verify_ack,
)


class SecureMessagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        cls.ed_a = NodeIdentityStore(root / "node-a")
        cls.ed_b = NodeIdentityStore(root / "node-b")
        cls.meta_a = cls.ed_a.initialize()
        cls.meta_b = cls.ed_b.initialize()
        cls.rsa_a = NodeRSAIdentityStore(cls.ed_a)
        cls.rsa_b = NodeRSAIdentityStore(cls.ed_b)
        cls.rsa_meta_a = cls.rsa_a.initialize()
        cls.rsa_meta_b = cls.rsa_b.initialize()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def make_envelope(self, text="Mensaje privado de prueba", message_id="message-test-1"):
        return seal_message(
            self.rsa_a, self.meta_b["node_id"], self.rsa_b.public_key_pem(), message_id, text
        )

    def test_hybrid_encryption_round_trip_and_ed25519_identity_is_preserved(self):
        before_a = self.ed_a.load()
        before_b = self.ed_b.load()
        envelope = self.make_envelope()
        self.assertNotIn("Mensaje privado", str(envelope))
        self.assertEqual(
            open_message(self.rsa_b, envelope, self.meta_a["node_id"], self.rsa_a.public_key_pem()),
            "Mensaje privado de prueba",
        )
        self.assertEqual(self.ed_a.load(), before_a)
        self.assertEqual(self.ed_b.load(), before_b)
        self.assertEqual(self.rsa_a.load()["node_id"], self.meta_a["node_id"])

    def test_modified_ciphertext_is_rejected_by_rsa_signature(self):
        envelope = self.make_envelope()
        envelope["ciphertext"] = envelope["ciphertext"][:-4] + "AAAA"
        with self.assertRaises(SecureMessagingError):
            open_message(self.rsa_b, envelope, self.meta_a["node_id"], self.rsa_a.public_key_pem())

    def test_sender_key_must_match_pinned_rsa_key(self):
        envelope = self.make_envelope()
        with self.assertRaises(SecureMessagingError):
            open_message(self.rsa_b, envelope, self.meta_a["node_id"], self.rsa_b.public_key_pem())

    def test_wrong_authenticated_sender_or_recipient_is_rejected(self):
        envelope = self.make_envelope()
        with self.assertRaises(SecureMessagingError):
            open_message(self.rsa_b, envelope, self.meta_b["node_id"], self.rsa_a.public_key_pem())
        with self.assertRaises(SecureMessagingError):
            open_message(self.rsa_a, envelope, self.meta_a["node_id"], self.rsa_a.public_key_pem())

    def test_ack_is_signed_and_bound_to_exact_message_and_nodes(self):
        message_id = "receipt-test-7"
        ack = create_ack(self.rsa_b, self.meta_a["node_id"], message_id)
        self.assertTrue(verify_ack(
            ack, self.meta_a["node_id"], self.meta_b["node_id"], message_id,
            self.rsa_b.public_key_pem(),
        ))
        self.assertFalse(verify_ack(
            ack, self.meta_a["node_id"], self.meta_b["node_id"], "another-message",
            self.rsa_b.public_key_pem(),
        ))
        modified = dict(ack)
        modified["status"] = "accepted-but-modified"
        self.assertFalse(verify_ack(
            modified, self.meta_a["node_id"], self.meta_b["node_id"], message_id,
            self.rsa_b.public_key_pem(),
        ))

    def test_private_rsa_key_file_permissions_are_restrictive(self):
        mode = self.rsa_a.private_key_path.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)


if __name__ == "__main__":
    unittest.main()
