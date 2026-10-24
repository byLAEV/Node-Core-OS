"""Reproducible integration tests for the user-level OpenPGP CLI."""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from openpgp.cli import OpenPGPError, OpenPGPManager


@unittest.skipUnless(shutil.which("gpg"), "GnuPG is required for OpenPGP integration tests")
class OpenPGPIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="node-core-openpgp-test-")
        self.root = Path(self.temporary.name)
        self.sender = OpenPGPManager(self.root / "sender" / "gnupg")
        self.recipient = OpenPGPManager(self.root / "recipient" / "gnupg")
        self.passphrase = "synthetic-test-passphrase-2026"
        self.sender_fingerprint = self.sender.generate_key(
            "Node Core Test Sender <sender@example.invalid>", self.passphrase
        )
        self.recipient_fingerprint = self.recipient.generate_key(
            "Node Core Test Recipient <recipient@example.invalid>", self.passphrase
        )
        self.plaintext = self.root / "message.txt"
        self.plaintext.write_text("Synthetic OpenPGP integration test.\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_encrypt_export_import_and_decrypt_between_independent_keyrings(self) -> None:
        sender_public = self.sender.export_public(self.sender_fingerprint, self.root / "sender-public.asc")
        self.recipient.import_public(sender_public)
        recipient_public = self.recipient.export_public(self.recipient_fingerprint, self.root / "recipient-public.asc")
        self.sender.import_public(recipient_public)
        encrypted = self.sender.encrypt(self.plaintext, self.root / "message.txt.gpg", self.recipient_fingerprint)
        decrypted = self.recipient.decrypt(encrypted, self.root / "decrypted.txt", self.passphrase)
        self.assertEqual(decrypted.read_bytes(), self.plaintext.read_bytes())
        self.assertNotEqual(encrypted.read_bytes(), self.plaintext.read_bytes())

    def test_detached_signature_is_valid_and_tampering_is_rejected(self) -> None:
        signature = self.sender.sign(
            self.plaintext, self.root / "message.txt.sig",
            self.sender_fingerprint, self.passphrase,
        )
        self.assertEqual(self.sender.verify(signature, self.plaintext), self.sender_fingerprint)
        changed = self.root / "tampered.txt"
        changed.write_text("Altered content.\n", encoding="utf-8")
        with self.assertRaises(OpenPGPError):
            self.sender.verify(signature, changed)

    def test_output_is_not_overwritten(self) -> None:
        existing = self.root / "existing.txt"
        existing.write_text("preserve me", encoding="utf-8")
        with self.assertRaises(OpenPGPError):
            self.sender.encrypt(self.plaintext, existing, self.recipient_fingerprint)
        self.assertEqual(existing.read_text(encoding="utf-8"), "preserve me")

    def test_fingerprint_must_be_full_hexadecimal_fingerprint(self) -> None:
        with self.assertRaises(OpenPGPError):
            self.sender.encrypt(self.plaintext, self.root / "bad.gpg", "1234ABCD")


if __name__ == "__main__":
    unittest.main()
