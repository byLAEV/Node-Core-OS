import json
from pathlib import Path
import tempfile
import unittest

from node_core.storage import StorageManager
from applications.p2p_contracts.p2p_contracts.service import (
    P2PContractsService, validate_btc_amount, validate_asset_code,
)


class FakeIdentityProfile:
    def load(self):
        return {"identity_id": "identity-test", "full_name": "Test User", "alias": "tester",
                "document_number": "TEST-000", "identity_status": "declared"}


class FakeNodeIdentity:
    peer_id = "QmTestPeerId012345678901234567890123456789"
    addresses = ("/ip4/127.0.0.1/tcp/4001/p2p/QmTestPeerId012345678901234567890123456789",)


class FakeNetwork:
    def identity(self):
        return FakeNodeIdentity()


class P2PContractsServiceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.storage = StorageManager(self.root / "storage")
        self.storage.initialize()
        self.service = P2PContractsService(self.storage, FakeIdentityProfile(), FakeNetwork())

    def test_btc_amount_is_validated_without_float(self):
        self.assertEqual(validate_btc_amount("0.01000000"), "0.01")
        with self.assertRaises(ValueError):
            validate_btc_amount("0")
        with self.assertRaises(ValueError):
            validate_btc_amount("0.000000001")

    def test_asset_must_differ_from_btc(self):
        self.assertEqual(validate_asset_code("usdt"), "USDT")
        with self.assertRaises(ValueError):
            validate_asset_code("BTC")

    def test_private_pgp_key_is_not_accepted_as_contact(self):
        with self.assertRaises(ValueError):
            self.service.create_btc_exchange_request(
                btc_amount="0.1", receive_asset="USDT", receive_amount="1",
                receive_network="", description="Test request",
                contacts=[{"type": "pgp_public_key", "value": "-----BEGIN PGP PRIVATE KEY BLOCK-----"}],
                publish_identity=False,
            )

    def test_create_request_and_find_request(self):
        result = self.service.create_btc_exchange_request(
            btc_amount="0.025", receive_asset="USDT", receive_amount="1500",
            receive_network="TRON", description="Test request",
            contacts=[{"type": "email", "value": "test@example.invalid"}],
            publish_identity=True,
        )
        found = self.service.find_request(result["request_id"])
        self.assertIsNotNone(found)
        self.assertEqual(found["request"]["exchange"]["give_amount"], "0.025")
        self.assertEqual(found["request"]["requester"]["identity_fields"]["full_name"], "Test User")
        self.assertEqual(found["request_status"], "open")
        self.assertEqual(self.service.current_manifest()["sequence"], 1)

    def test_evidence_closes_request_and_lookup_returns_evidence(self):
        request = self.service.create_btc_exchange_request(
            btc_amount="0.01", receive_asset="EUR", receive_amount="500",
            receive_network="", description="Test request",
            contacts=[{"type": "phone", "value": "+000000"}], publish_identity=False,
        )
        evidence = self.service.create_request_evidence(
            request_id=request["request_id"], outcome="exchange_completed",
            evidence_type="exchange_result", description="The parties report completion.",
            reporter_statement="Self-reported test evidence.",
        )
        found = self.service.find_request(request["request_id"])
        self.assertEqual(found["request_status"], "exchange_completed")
        self.assertEqual(len(found["evidence"]), 1)
        self.assertEqual(found["evidence"][0]["evidence_id"], evidence["evidence_id"])
        self.assertEqual(self.service.current_manifest()["sequence"], 2)

    def test_closure_records_counterparty_and_rating(self):
        request = self.service.create_btc_exchange_request(
            btc_amount="0.02", receive_asset="EUR", receive_amount="600",
            receive_network="", description="Test closure request",
            contacts=[{"type": "email", "value": "test@example.invalid"}], publish_identity=False,
        )
        evidence = self.service.create_request_evidence(
            request_id=request["request_id"], outcome="exchange_completed",
            evidence_type="exchange_result", description="Exchange reported complete.",
            reporter_statement="Test reporter statement.", target_node_id="peer-counterparty", rating=5,
        )
        found = self.service.find_request(request["request_id"])
        self.assertEqual(found["evidence"][0]["target_node_id"], "peer-counterparty")
        self.assertEqual(found["evidence"][0]["rating"], 5)
        self.assertEqual(evidence["verification_status"], "self_reported_unverified")

    def test_invalid_reputation_rating_is_rejected(self):
        request = self.service.create_btc_exchange_request(
            btc_amount="0.02", receive_asset="EUR", receive_amount="600",
            receive_network="", description="Test closure request",
            contacts=[{"type": "email", "value": "test@example.invalid"}], publish_identity=False,
        )
        with self.assertRaises(ValueError):
            self.service.create_request_evidence(
                request_id=request["request_id"], outcome="exchange_completed",
                evidence_type="exchange_result", description="Exchange reported complete.",
                reporter_statement="Test reporter statement.", target_node_id="peer-counterparty", rating=6,
            )

    def test_manifest_tampering_is_detected(self):
        self.service.create_btc_exchange_request(
            btc_amount="0.1", receive_asset="ETH", receive_amount="1",
            receive_network="Ethereum", description="Test request",
            contacts=[{"type": "other", "value": "test contact"}], publish_identity=False,
        )
        head = json.loads((self.root / "storage/p2p_contracts/head.json").read_text())
        manifest_path = self.root / "storage" / head["manifest_path"]
        manifest = json.loads(manifest_path.read_text())
        manifest["requests"][0]["status"] = "closed"
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(Exception):
            self.service.current_manifest()


if __name__ == "__main__":
    unittest.main()
