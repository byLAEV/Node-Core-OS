import json
import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.relay_delivery import (
    canonical_json_bytes,
    create_request,
    persist_and_sign_receipt,
    verify_request,
)

KEY = "12" * 32


class RelayDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.identity = NodeIdentityStore(self.root / "data")
        self.identity.initialize()
        self.payload = {
            "kind": "synthetic_delivery_test",
            "message": "Node Core OS relay delivery test; no personal data.",
        }

    def test_valid_request_verifies_and_persists_under_local_storage(self):
        envelope = create_request("gha-123-1", self.payload, KEY)
        verified = verify_request(envelope, KEY)
        receipt = persist_and_sign_receipt(self.root / "data", verified, self.identity)

        saved = Path(receipt["persisted_path"])
        self.assertTrue(saved.is_file())
        self.assertEqual(saved.parent, self.root / "data" / "storage" / "relay" / "inbox")
        self.assertEqual(saved.name, "gha-123-1.json")
        record = json.loads(saved.read_text(encoding="utf-8"))
        self.assertEqual(record["run_id"], "gha-123-1")
        self.assertEqual(record["payload"], self.payload)
        self.assertEqual(record["payload_sha256"], verified["payload_sha256"])
        self.assertEqual(receipt["status"], "persisted")
        self.assertEqual(receipt["node_id"], self.identity.load()["node_id"])

        signature = bytes.fromhex(receipt.pop("signature_ed25519"))
        self.assertTrue(NodeIdentityStore.verify(
            receipt["public_key"], canonical_json_bytes(receipt), signature
        ))

    def test_wrong_hmac_key_is_rejected(self):
        envelope = create_request("gha-123-1", self.payload, KEY)
        with self.assertRaisesRegex(ValueError, "HMAC"):
            verify_request(envelope, "34" * 32)

    def test_payload_tampering_is_rejected_before_storage(self):
        envelope = create_request("gha-123-1", self.payload, KEY)
        envelope["payload"]["message"] = "tampered"
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            verify_request(envelope, KEY)
        self.assertFalse((self.root / "data" / "storage" / "relay").exists())

    def test_hmac_tampering_is_rejected(self):
        envelope = create_request("gha-123-1", self.payload, KEY)
        envelope["hmac_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "HMAC"):
            verify_request(envelope, KEY)

    def test_invalid_run_id_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "run_id"):
            create_request("../escape", self.payload, KEY)

    def test_invalid_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "64 hexadecimal"):
            create_request("gha-123-1", self.payload, "short")

    def test_existing_run_id_cannot_be_overwritten_with_different_payload(self):
        first = verify_request(create_request("gha-123-1", self.payload, KEY), KEY)
        persist_and_sign_receipt(self.root / "data", first, self.identity)
        second_payload = {**self.payload, "message": "different"}
        second = verify_request(create_request("gha-123-1", second_payload, KEY), KEY)
        with self.assertRaisesRegex(RuntimeError, "refusing overwrite"):
            persist_and_sign_receipt(self.root / "data", second, self.identity)

    def test_same_request_retry_keeps_persisted_content(self):
        verified = verify_request(create_request("gha-123-1", self.payload, KEY), KEY)
        first = persist_and_sign_receipt(self.root / "data", verified, self.identity)
        original = Path(first["persisted_path"]).read_bytes()
        second = persist_and_sign_receipt(self.root / "data", verified, self.identity)
        self.assertEqual(Path(second["persisted_path"]).read_bytes(), original)
        self.assertEqual(first["payload_sha256"], second["payload_sha256"])


if __name__ == "__main__":
    unittest.main()
