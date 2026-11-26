import base64
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from node_pki_guard_cli.cli import VerificationError, verify_receipt


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL is required")
class ReceiptOpenSSLTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.private = self.root / "receipt-private.pem"
        self.public = self.root / "receipt-public.pem"
        subprocess.run([
            "openssl", "genpkey", "-algorithm", "ED25519",
            "-out", str(self.private),
        ], check=True, capture_output=True)
        subprocess.run([
            "openssl", "pkey", "-in", str(self.private), "-pubout",
            "-out", str(self.public),
        ], check=True, capture_output=True)
        self.receipt = {
            "schema": "node-core-os/node-pki-guard-issuance-receipt/v1",
            "operation_id": "test-operation-001",
            "certificate_fingerprint_sha256": "a" * 64,
            "receipt_key_id": "test-receipt-key-01",
        }
        self.envelope = self.root / "receipt.json"
        self.signature = self.root / "receipt.sig"
        self.envelope.write_text(json.dumps({
            "key_id": "test-receipt-key-01",
            "receipt": self.receipt,
        }, sort_keys=True), encoding="utf-8")
        canonical = json.dumps(
            self.receipt, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False,
        ).encode("utf-8")
        data = self.root / "canonical.json"
        data.write_bytes(canonical)
        raw_signature = self.root / "signature.raw"
        subprocess.run([
            "openssl", "pkeyutl", "-sign", "-inkey", str(self.private),
            "-rawin", "-in", str(data), "-out", str(raw_signature),
        ], check=True, capture_output=True)
        self.signature.write_text(
            base64.urlsafe_b64encode(raw_signature.read_bytes()).rstrip(b"=").decode("ascii"),
            encoding="ascii",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_receipt_signature(self):
        result = verify_receipt(
            receipt_file=self.envelope,
            signature_file=self.signature,
            public_key_file=self.public,
            expected_key_id="test-receipt-key-01",
            algorithm="ed25519",
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["operation_id"], "test-operation-001")

    def test_wrong_key_identifier_is_rejected(self):
        with self.assertRaises(VerificationError):
            verify_receipt(
                receipt_file=self.envelope,
                signature_file=self.signature,
                public_key_file=self.public,
                expected_key_id="attacker-key",
                algorithm="ed25519",
            )

    def test_tampered_receipt_is_rejected(self):
        changed = dict(self.receipt)
        changed["operation_id"] = "tampered-operation"
        self.envelope.write_text(json.dumps({
            "key_id": "test-receipt-key-01",
            "receipt": changed,
        }), encoding="utf-8")
        with self.assertRaises(VerificationError):
            verify_receipt(
                receipt_file=self.envelope,
                signature_file=self.signature,
                public_key_file=self.public,
                expected_key_id="test-receipt-key-01",
                algorithm="ed25519",
            )


if __name__ == "__main__":
    unittest.main()
