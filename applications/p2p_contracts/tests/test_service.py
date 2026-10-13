import json
from pathlib import Path
import tempfile
import unittest

from node_core.storage import StorageManager
from applications.p2p_contracts.p2p_contracts.service import (
    MANIFEST_SCHEMA, P2PContractsService, document_hash,
    validate_btc_amount, validate_asset_code,
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

    def test_genesis_is_in_manifest_directory_and_anchors_block_one(self):
        genesis_path = self.root / "storage" / "p2p_contracts" / "manifests" / "genesis-manifest.json"
        self.assertTrue(genesis_path.is_file())
        genesis = json.loads(genesis_path.read_text(encoding="utf-8"))
        root_hash = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
        self.assertEqual(genesis["genesis_hash"], root_hash)
        self.assertEqual(genesis["references"]["bitcoin_genesis_block"]["block_hash"], root_hash)

        result = self.service.create_btc_exchange_request(
            btc_amount="0.025", receive_asset="USDT", receive_amount="1500",
            receive_network="TRON", description="Genesis reference test",
            contacts=[{"type": "email", "value": "test@example.invalid"}],
            publish_identity=True,
        )
        manifest = result["manifest_document"]
        self.assertEqual(manifest["sequence"], 1)
        self.assertEqual(manifest["genesis_hash"], root_hash)
        self.assertEqual(manifest["previous_manifest_hash"], root_hash)
        self.assertEqual(Path(result["manifest_path"]).parent, genesis_path.parent)

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

    def test_remote_request_batch_is_imported_as_one_manifest(self):
        requests = []
        for amount in ("0.01", "0.02"):
            result = self.service.create_btc_exchange_request(
                btc_amount=amount, receive_asset="USDT", receive_amount="100",
                receive_network="TRON", description="Remote batch test",
                contacts=[{"type": "email", "value": "test@example.invalid"}],
                publish_identity=False,
            )
            requests.append(json.loads(Path(result["request_path"]).read_text(encoding="utf-8")))
        remote_root = self.root / "remote-storage"
        remote_storage = StorageManager(remote_root)
        remote_storage.initialize()
        remote_service = P2PContractsService(remote_storage, FakeIdentityProfile(), FakeNetwork())
        result = remote_service.import_remote_requests(requests)
        self.assertEqual(result["imported_count"], 2)
        self.assertEqual(remote_service.current_manifest()["sequence"], 1)
        self.assertIsNotNone(remote_service.find_request(requests[0]["request_id"]))
        self.assertIsNotNone(remote_service.find_request(requests[1]["request_id"]))
        duplicate = remote_service.import_remote_requests(requests)
        self.assertEqual(duplicate["imported_count"], 0)
        self.assertEqual(remote_service.current_manifest()["sequence"], 1)

    def test_remote_evidence_is_verified_and_imported(self):
        request = self.service.create_btc_exchange_request(
            btc_amount="0.03", receive_asset="EUR", receive_amount="700",
            receive_network="", description="Evidence sync test",
            contacts=[{"type": "email", "value": "test@example.invalid"}],
            publish_identity=False,
        )
        remote_root = self.root / "evidence-remote-storage"
        remote_storage = StorageManager(remote_root)
        remote_storage.initialize()
        remote_service = P2PContractsService(remote_storage, FakeIdentityProfile(), FakeNetwork())
        request_doc = json.loads(Path(request["request_path"]).read_text(encoding="utf-8"))
        remote_service.import_remote_requests([request_doc])
        evidence = self.service.create_request_evidence(
            request_id=request["request_id"], outcome="exchange_completed",
            evidence_type="exchange_result", description="Completed for synchronization test.",
            reporter_statement="Self-reported evidence from source node.",
            target_node_id="peer-counterparty", rating=4,
        )
        evidence_path = self.root / "storage" / "p2p_contracts" / "evidence" / f"{evidence['evidence_id']}.json"
        evidence_doc = json.loads(evidence_path.read_text(encoding="utf-8"))
        imported = remote_service.import_remote_evidence(evidence_doc)
        self.assertTrue(imported["imported"])
        found = remote_service.find_request(request["request_id"])
        self.assertEqual(found["request_status"], "exchange_completed")
        self.assertEqual(found["evidence"][0]["rating"], 4)
        self.assertEqual(found["evidence"][0]["target_node_id"], "peer-counterparty")
        self.assertFalse(remote_service.import_remote_evidence(evidence_doc)["imported"])

    def test_remote_manifest_rejects_non_object_index_entries(self):
        request = self.service.create_btc_exchange_request(
            btc_amount="0.1", receive_asset="ETH", receive_amount="1",
            receive_network="Ethereum", description="Malformed manifest regression test",
            contacts=[{"type": "other", "value": "synthetic test contact"}],
            publish_identity=False,
        )
        request_document = json.loads(Path(request["request_path"]).read_text(encoding="utf-8"))

        remote_root = self.root / "malformed-manifest-remote-storage"
        remote_storage = StorageManager(remote_root)
        remote_storage.initialize()
        remote_service = P2PContractsService(remote_storage, FakeIdentityProfile(), FakeNetwork())

        payload = {
            "schema": MANIFEST_SCHEMA,
            "application_id": "node-core-os-p2p-contracts",
            "application_version": "0.1.0-dev",
            "protocol_version": "0.1.0",
            "sequence": 1,
            "genesis_hash": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
            "previous_manifest_hash": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
            "created_at": "2026-01-01T00:00:00Z",
            "requests": [None],
            "evidence": [],
        }
        malformed_manifest = {**payload, "manifest_hash": document_hash(payload)}

        with self.assertRaisesRegex(ValueError, "request index entries must be JSON objects"):
            remote_service.import_remote_manifest(
                malformed_manifest,
                request_documents=[request_document],
            )
        self.assertIsNone(remote_service.current_manifest())

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
