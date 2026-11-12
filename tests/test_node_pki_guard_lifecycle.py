import unittest

from cryptography.hazmat.primitives.asymmetric import ed25519

from node_core.security.node_pki_guard_lifecycle import PKILifecycleService


class PKILifecycleReceiptTests(unittest.TestCase):
    def test_signed_receipt_verifies(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        payload = {
            "schema": "node-core-os/node-pki-guard-issuance-receipt/v1",
            "operation_id": "operation-001",
            "certificate_fingerprint_sha256": "a" * 64,
        }
        pem = private_key.private_bytes_raw()
        # The production API accepts PEM, so serialize the test key in PKCS8.
        from cryptography.hazmat.primitives import serialization
        pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        signature = PKILifecycleService._sign_receipt(payload, pem, None)
        self.assertTrue(PKILifecycleService.verify_receipt_signature(
            payload, signature, public_key
        ))

    def test_altered_receipt_does_not_verify(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        from cryptography.hazmat.primitives import serialization
        pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        payload = {"operation_id": "operation-001"}
        signature = PKILifecycleService._sign_receipt(payload, pem, None)
        altered = {"operation_id": "operation-002"}
        self.assertFalse(PKILifecycleService.verify_receipt_signature(
            altered, signature, private_key.public_key()
        ))


if __name__ == "__main__":
    unittest.main()
