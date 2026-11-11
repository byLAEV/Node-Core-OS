import unittest

from node_core.security.node_pki_guard import AuthorizationDecision
from node_core.security.node_pki_guard_utxo import (
    FinalityProof,
    SpendRequest,
    SpendSubmission,
    UTXOBackendError,
    consume_authorization,
)


class FakeAtomicBackend:
    def __init__(self):
        self.submissions = {}
        self.spend_calls = 0

    def get_idempotent_result(self, idempotency_key):
        return self.submissions.get(idempotency_key)

    def submit_spend_atomic(self, request):
        self.spend_calls += 1
        result = SpendSubmission(
            transaction_id="tx-final-001",
            outpoint=request.outpoint,
            operation_id=request.operation_id,
            operation_hash=request.operation_hash,
            state="SUBMITTED",
        )
        self.submissions[request.idempotency_key] = result
        return result

    def wait_for_finality(self, transaction_id, timeout_seconds):
        return FinalityProof(
            transaction_id=transaction_id,
            block_id="block-final-001",
            finalized_height=42,
            proof_format="test-finality-v1",
            proof_data={"test": True},
        )

    def verify_finality_proof(self, proof, transaction_id):
        return proof.transaction_id == transaction_id and proof.finalized_height == 42


class UTXOBackendContractTests(unittest.TestCase):
    def setUp(self):
        self.request = SpendRequest(
            operation_id="operation-001",
            idempotency_key="idem-001",
            operation_hash="a" * 64,
            authorization_id="authorization-001",
            outpoint="b" * 64 + ":0",
            binding_id="binding-001",
            policy_id="policy-001",
            policy_version="1",
        )
        self.decision = AuthorizationDecision(
            decision="PROTECTED",
            reason="local preconditions passed",
            operation_hash=self.request.operation_hash,
            authorization_id=self.request.authorization_id,
            outpoint=self.request.outpoint,
        )
        self.backend = FakeAtomicBackend()

    def test_spend_requires_verified_finality(self):
        result = consume_authorization(
            decision=self.decision, request=self.request, backend=self.backend,
        )
        self.assertEqual(result.submission.state, "FINALIZED")
        self.assertEqual(result.finality.finalized_height, 42)
        self.assertEqual(self.backend.spend_calls, 1)

    def test_retries_reuse_durable_idempotent_submission(self):
        first = consume_authorization(
            decision=self.decision, request=self.request, backend=self.backend,
        )
        second = consume_authorization(
            decision=self.decision, request=self.request, backend=self.backend,
        )
        self.assertEqual(first.submission.transaction_id, second.submission.transaction_id)
        self.assertEqual(self.backend.spend_calls, 1)

    def test_non_protected_decision_cannot_spend(self):
        denied = AuthorizationDecision("DENY", "denied", self.request.operation_hash)
        with self.assertRaises(UTXOBackendError):
            consume_authorization(
                decision=denied, request=self.request, backend=self.backend,
            )
        self.assertEqual(self.backend.spend_calls, 0)

    def test_outpoint_mismatch_cannot_spend(self):
        wrong = AuthorizationDecision(
            "PROTECTED", "approved", self.request.operation_hash,
            self.request.authorization_id, "c" * 64 + ":0",
        )
        with self.assertRaises(UTXOBackendError):
            consume_authorization(decision=wrong, request=self.request, backend=self.backend)
        self.assertEqual(self.backend.spend_calls, 0)

    def test_operation_hash_mismatch_cannot_spend(self):
        wrong = AuthorizationDecision(
            "PROTECTED", "approved", "d" * 64,
            self.request.authorization_id, self.request.outpoint,
        )
        with self.assertRaises(UTXOBackendError):
            consume_authorization(decision=wrong, request=self.request, backend=self.backend)
        self.assertEqual(self.backend.spend_calls, 0)

    def test_invalid_finality_proof_rejected(self):
        class BadProofBackend(FakeAtomicBackend):
            def verify_finality_proof(self, proof, transaction_id):
                return False
        with self.assertRaises(UTXOBackendError):
            consume_authorization(
                decision=self.decision, request=self.request, backend=BadProofBackend(),
            )

    def test_idempotency_conflict_rejected(self):
        self.backend.submissions[self.request.idempotency_key] = SpendSubmission(
            "tx-other", self.request.outpoint, "other-operation",
            self.request.operation_hash, "SUBMITTED",
        )
        with self.assertRaises(UTXOBackendError):
            consume_authorization(
                decision=self.decision, request=self.request, backend=self.backend,
            )
        self.assertEqual(self.backend.spend_calls, 0)


if __name__ == "__main__":
    unittest.main()
