import json
import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.relay_delivery import (
    create_request, persist_and_sign_receipt, verify_request, canonical_json_bytes
)
from applications.relay.relay_sender import verify_receipt


KEY = "11" * 32


class RelayDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = {"schema": "node-core-os/test-manifest/v1", "synthetic": True}
        self.envelope = create_request("gha-123-1", self.payload, KEY)

    def test_request_authenticates_payload_and_detects_tampering(self):
        verified = verify_request(self.envelope, KEY)
        self.assertEqual(verified["payload"], self.payload)
        modified = dict(self.envelope)
        modified["payload"] = {"synthetic": False}
        with self.assertRaises(ValueError):
            verify_request(modified, KEY)

    def test_invalid_hmac_is_rejected(self):
        modified = dict(self.envelope, hmac_sha256="0" * 64)
        with self.assertRaises(ValueError):
            verify_request(modified, KEY)

    def test_payload_is_persisted_and_receipt_signature_is_verifiable(self):
        identity = NodeIdentityStore(self.root / ".node-core")
        verified = verify_request(self.envelope, KEY)
        receipt = persist_and_sign_receipt(self.root / ".node-core", verified, identity)
        path = Path(receipt["persisted_path"])
        self.assertTrue(path.is_file())
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["payload"], self.payload)
        verify_receipt(receipt, "gha-123-1", verified["payload_sha256"], identity.load()["public_key"])

    def test_receipt_tampering_is_rejected(self):
        identity = NodeIdentityStore(self.root / ".node-core")
        verified = verify_request(self.envelope, KEY)
        receipt = persist_and_sign_receipt(self.root / ".node-core", verified, identity)
        altered = dict(receipt, payload_sha256="0" * 64)
        with self.assertRaises(ValueError):
            verify_receipt(altered, "gha-123-1", verified["payload_sha256"], identity.load()["public_key"])

    def test_existing_run_id_cannot_be_overwritten_with_different_content(self):
        identity = NodeIdentityStore(self.root / ".node-core")
        persist_and_sign_receipt(self.root / ".node-core", verify_request(self.envelope, KEY), identity)
        other = create_request("gha-123-1", {"changed": True}, KEY)
        with self.assertRaises(RuntimeError):
            persist_and_sign_receipt(self.root / ".node-core", verify_request(other, KEY), identity)


if __name__ == "__main__":
    unittest.main()
