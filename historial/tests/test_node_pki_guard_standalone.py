import tempfile
import threading
import unittest
from pathlib import Path

from node_core.security.node_pki_guard_backend import (
    AuthorizationUTXO,
    BackendContractError,
    CommitKind,
    IdempotencyConflict,
    SpendRequest,
    SpendState,
    UTXOStatus,
)
from node_core.security.backends.standalone_sqlite import StandaloneSQLiteBackend


class StandaloneSQLiteBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "guard.sqlite3"
        self.backend = StandaloneSQLiteBackend(self.db)
        self.authorization = AuthorizationUTXO(
            outpoint="a" * 64 + ":0",
            authorization_id="auth-001",
            binding_id="binding-001",
            node_id="node-001",
            owner_key_id="owner-key-001",
            operation_hash="b" * 64,
            policy_id="policy-001",
            policy_version="1",
        )
        self.backend.register_authorization(self.authorization)
        self.request = SpendRequest(
            operation_id="operation-001",
            idempotency_key="idem-001",
            request_hash="c" * 64,
            operation_hash="b" * 64,
            authorization_id="auth-001",
            outpoint="a" * 64 + ":0",
            binding_id="binding-001",
            node_id="node-001",
            owner_key_id="owner-key-001",
            policy_id="policy-001",
            policy_version="1",
        )

    def tearDown(self):
        self.temp.cleanup()


    def test_authorization_payload_hash_survives_restart(self):
        from node_core.security.node_pki_guard_backend import AuthorizationUTXO

        committed = AuthorizationUTXO(
            outpoint="e" * 64 + ":1",
            authorization_id="auth-hash-001",
            binding_id="binding-001",
            node_id="node-001",
            owner_key_id="owner-key-001",
            operation_hash="d" * 64,
            policy_id="policy-001",
            policy_version="1",
            authorization_payload_hash="f" * 64,
        )
        self.backend.register_authorization(committed)
        reopened = StandaloneSQLiteBackend(self.db)
        stored = reopened.get_authorization(committed.outpoint)
        self.assertEqual(stored, committed)

    def test_conflicting_authorization_payload_hash_is_rejected(self):
        from node_core.security.node_pki_guard_backend import AuthorizationUTXO

        committed = AuthorizationUTXO(
            outpoint="e" * 64 + ":1",
            authorization_id="auth-hash-002",
            binding_id="binding-001",
            node_id="node-001",
            owner_key_id="owner-key-001",
            operation_hash="d" * 64,
            policy_id="policy-001",
            policy_version="1",
            authorization_payload_hash="f" * 64,
        )
        self.backend.register_authorization(committed)
        altered = AuthorizationUTXO(
            outpoint=committed.outpoint,
            authorization_id=committed.authorization_id,
            binding_id=committed.binding_id,
            node_id=committed.node_id,
            owner_key_id=committed.owner_key_id,
            operation_hash=committed.operation_hash,
            policy_id=committed.policy_id,
            policy_version=committed.policy_version,
            authorization_payload_hash="0" * 64,
        )
        with self.assertRaises(BackendContractError):
            self.backend.register_authorization(altered)

    def test_register_and_query_authorization(self):
        self.assertEqual(self.backend.get_utxo_status(self.request.outpoint), UTXOStatus.UNSPENT)
        self.assertEqual(self.backend.get_utxo_status("d" * 64 + ":1"), UTXOStatus.NOT_FOUND)

    def test_atomic_spend_and_local_commit_evidence(self):
        submission = self.backend.submit_spend_atomic(self.request)
        self.assertEqual(submission.state, SpendState.LOCAL_COMMITTED)
        self.assertEqual(self.backend.get_utxo_status(self.request.outpoint), UTXOStatus.SPENT)
        evidence = self.backend.wait_for_commit(submission.transaction_id, 1.0)
        self.assertEqual(evidence.commit_kind, CommitKind.LOCAL_ACID)
        self.assertTrue(self.backend.verify_commit_evidence(evidence, submission.transaction_id))
        self.assertEqual(self.backend.get_receipt(submission.transaction_id)["operation_id"], "operation-001")

    def test_same_idempotent_request_returns_same_transaction(self):
        first = self.backend.submit_spend_atomic(self.request)
        second = self.backend.submit_spend_atomic(self.request)
        self.assertEqual(first.transaction_id, second.transaction_id)
        self.assertEqual(self.backend.get_idempotent_result("idem-001"), first)

    def test_idempotency_key_conflict_is_rejected(self):
        self.backend.submit_spend_atomic(self.request)
        conflicting = SpendRequest(
            operation_id=self.request.operation_id,
            idempotency_key=self.request.idempotency_key,
            request_hash="e" * 64,
            operation_hash=self.request.operation_hash,
            authorization_id=self.request.authorization_id,
            outpoint=self.request.outpoint,
            binding_id=self.request.binding_id,
            node_id=self.request.node_id,
            owner_key_id=self.request.owner_key_id,
            policy_id=self.request.policy_id,
            policy_version=self.request.policy_version,
        )
        with self.assertRaises(IdempotencyConflict):
            self.backend.submit_spend_atomic(conflicting)

    def test_wrong_owner_or_context_cannot_spend(self):
        wrong = SpendRequest(
            operation_id="operation-002",
            idempotency_key="idem-002",
            request_hash="f" * 64,
            operation_hash=self.request.operation_hash,
            authorization_id=self.request.authorization_id,
            outpoint=self.request.outpoint,
            binding_id=self.request.binding_id,
            node_id=self.request.node_id,
            owner_key_id="attacker-key",
            policy_id=self.request.policy_id,
            policy_version=self.request.policy_version,
        )
        with self.assertRaises(BackendContractError):
            self.backend.submit_spend_atomic(wrong)
        self.assertEqual(self.backend.get_utxo_status(self.request.outpoint), UTXOStatus.UNSPENT)

    def test_second_operation_cannot_double_spend(self):
        self.backend.submit_spend_atomic(self.request)
        second = SpendRequest(
            operation_id="operation-002",
            idempotency_key="idem-002",
            request_hash="1" * 64,
            operation_hash=self.request.operation_hash,
            authorization_id=self.request.authorization_id,
            outpoint=self.request.outpoint,
            binding_id=self.request.binding_id,
            node_id=self.request.node_id,
            owner_key_id=self.request.owner_key_id,
            policy_id=self.request.policy_id,
            policy_version=self.request.policy_version,
        )
        with self.assertRaises(BackendContractError):
            self.backend.submit_spend_atomic(second)

    def test_duplicate_registration_with_conflicting_content_rejected(self):
        conflicting = AuthorizationUTXO(
            outpoint=self.authorization.outpoint,
            authorization_id="auth-other",
            binding_id=self.authorization.binding_id,
            node_id=self.authorization.node_id,
            owner_key_id=self.authorization.owner_key_id,
            operation_hash=self.authorization.operation_hash,
            policy_id=self.authorization.policy_id,
            policy_version=self.authorization.policy_version,
        )
        with self.assertRaises(BackendContractError):
            self.backend.register_authorization(conflicting)

    def test_network_fee_is_not_accepted_by_standalone(self):
        with self.assertRaises(BackendContractError):
            self.backend.submit_spend_atomic(SpendRequest(
                operation_id="operation-fee",
                idempotency_key="idem-fee",
                request_hash="2" * 64,
                operation_hash=self.request.operation_hash,
                authorization_id=self.request.authorization_id,
                outpoint="f" * 64 + ":0",
                binding_id=self.request.binding_id,
                node_id=self.request.node_id,
                owner_key_id=self.request.owner_key_id,
                policy_id=self.request.policy_id,
                policy_version=self.request.policy_version,
                fee_amount=10,
                fee_asset="NODE",
            ))

    def test_concurrent_competing_spends_only_one_succeeds(self):
        second = SpendRequest(
            operation_id="operation-race",
            idempotency_key="idem-race",
            request_hash="3" * 64,
            operation_hash=self.request.operation_hash,
            authorization_id=self.request.authorization_id,
            outpoint=self.request.outpoint,
            binding_id=self.request.binding_id,
            node_id=self.request.node_id,
            owner_key_id=self.request.owner_key_id,
            policy_id=self.request.policy_id,
            policy_version=self.request.policy_version,
        )
        barrier = threading.Barrier(2)
        outcomes = []

        def spend(request):
            barrier.wait()
            try:
                outcomes.append(("ok", self.backend.submit_spend_atomic(request)))
            except BackendContractError:
                outcomes.append(("rejected", None))

        threads = [
            threading.Thread(target=spend, args=(self.request,)),
            threading.Thread(target=spend, args=(second,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(sum(1 for status, _ in outcomes if status == "ok"), 1)
        self.assertEqual(sum(1 for status, _ in outcomes if status == "rejected"), 1)
        self.assertEqual(self.backend.get_utxo_status(self.request.outpoint), UTXOStatus.SPENT)

    def test_evidence_tampering_is_detected(self):
        submission = self.backend.submit_spend_atomic(self.request)
        evidence = self.backend.wait_for_commit(submission.transaction_id, 1.0)
        tampered = type(evidence)(
            transaction_id=evidence.transaction_id,
            commit_kind=evidence.commit_kind,
            backend_id=evidence.backend_id,
            committed_at_utc=evidence.committed_at_utc,
            sequence=evidence.sequence,
            evidence_hash="0" * 64,
            external_proof=evidence.external_proof,
        )
        self.assertFalse(self.backend.verify_commit_evidence(tampered, submission.transaction_id))


if __name__ == "__main__":
    unittest.main()
