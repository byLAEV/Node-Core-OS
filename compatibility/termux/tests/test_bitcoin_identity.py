#!/usr/bin/env python3
"""Deterministic, public Bitcoin scalar fixtures for local proof-gate tests.

These keys are intentionally public, compromised test vectors. Never fund them,
use them for wallets, or reuse this test-only material in production.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bitcoin_identity import BitcoinIdentityError, BitcoinIdentityGate


TEST_PRIVATE_KEYS = (
    "0000000000000000000000000000000000000000000000000000000000000001",
    "1111111111111111111111111111111111111111111111111111111111111111",
    "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
)


class BitcoinIdentityFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.gate = BitcoinIdentityGate(self.state)

    def issue_challenge(self):
        return self.gate.issue_challenge(
            full_name="Synthetic Test Operator",
            document_number="",
            nationality="",
            birth_date="01/01/1990",
            height_cm=175,
        )

    def test_public_deterministic_scalars_prove_control_without_persisting_private_keys(self):
        for private_key_hex in TEST_PRIVATE_KEYS:
            with self.subTest(private_key=private_key_hex[:8]):
                challenge = self.issue_challenge()
                status = self.gate.verify_private_key_and_stage(
                    challenge_id=challenge["challenge_id"],
                    private_key_hex=private_key_hex,
                )
                self.assertEqual(status["status"], "control_verified")
                self.assertEqual(status["network"], "mainnet")
                self.assertTrue(status["address"].startswith("bc1q"))
                self.assertTrue(status["installation_gate_ready"])
                pending_text = self.gate.pending_path.read_text(encoding="utf-8")
                pending = json.loads(pending_text)
                self.assertNotIn(private_key_hex, pending_text)
                self.assertNotIn("private_key_hex", pending)
                self.assertEqual(pending["bitcoin"]["network"], "mainnet")
                self.assertEqual(pending["proof"]["status"], "control_verified")
                with self.assertRaisesRegex(BitcoinIdentityError, "unknown, expired, or already used"):
                    self.gate.verify_private_key_and_stage(
                        challenge_id=challenge["challenge_id"],
                        private_key_hex=private_key_hex,
                    )

    def test_invalid_scalars_and_encodings_are_rejected(self):
        challenge = self.issue_challenge()
        with self.assertRaisesRegex(BitcoinIdentityError, "64 hexadecimal"):
            self.gate.verify_private_key_and_stage(
                challenge_id=challenge["challenge_id"],
                private_key_hex="1",
            )

        challenge = self.issue_challenge()
        with self.assertRaisesRegex(BitcoinIdentityError, "scalar is outside"):
            self.gate.verify_private_key_and_stage(
                challenge_id=challenge["challenge_id"],
                private_key_hex="0" * 64,
            )


if __name__ == "__main__":
    unittest.main()
