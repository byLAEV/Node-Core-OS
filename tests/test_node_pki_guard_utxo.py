import unittest

from node_core.security.node_pki_guard import AuthorizationDecision
from node_core.security.node_pki_guard_backend import (
    AuthorizationUTXO,
    CommitEvidence,
    CommitKind,
    SpendRequest,
    SpendState,
    SpendSubmission,
    UTXOAuthorizationBackend,
    UTXOStatus,
    compute_spend_request_hash,
)
from node_core.security.node_pki_guard_utxo import UTXOBackendError, consume_authorization


class FakeBackend(UTXOAuthorizationBackend):
    def __init__(self):
        self.records = {}
        self.submissions = {}
        self.calls = 0

    def register_authorization(self, authorization):
        self.records[authorization.outpoint] = authorization

    def get_utxo_status(self, outpoint):
        return UTXOStatus.UNSPENT if outpoint in self.records else UTXOStatus.NOT_FOUND

    def get_authorization(self, outpoint):
        return self.records.get(outpoint)

    def get_idempotent_result(self, idempotency_key):
        return self.submissions.get(idempotency_key)

    def submit_spend_atomic(self, request):
        self.calls += 1
        result = SpendSubmission(
            transaction_id="tx-001",
            request_hash=request.request_hash,
            outpoint=request.outpoint,
            operation_id=request.operation_id,
            idempotency_key=request.idempotency_key,
            operation_hash=request.operation_hash,
            authorization_id=request.authorization_id,
            state=SpendState.LOCAL_COMMITTED,
        )
        self.submissions[request.idempotency_key] = result
        return result

    def wait_for_commit(self, transaction_id, timeout_seconds):
        return CommitEvidence(
            transaction_id=transaction_id,
            commit_kind=CommitKind.LOCAL_ACID,
            backend_id="test-fake",
            committed_at_utc="2026-01-01T00:00:00+00:00",
            sequence=1,
            evidence_hash="a" * 64,
            external_proof={"test": True},
        )

    def verify_commit_evidence(self, evidence, transaction_id):
        return evidence.transaction_id == transaction_id and evidence.commit_kind is CommitKind.LOCAL_ACID


class SharedUTXOCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.backend = FakeBackend()
        self.outpoint = "a" * 64 + ":0"
        self.auth = AuthorizationUTXO(
            outpoint=self.outpoint,
            authorization_id="auth-1",
            binding_id="binding-1",
            node_id="node-1",
            owner_key_id="owner-1",
            operation_hash="b" * 64,
            policy_id="policy-1",
            policy_version="1",
        )
        self.backend.register_authorization(self.auth)
        values = dict(
            operation_id="op-1",
            idempotency_key="idem-1",
            operation_hash="b" * 64,
            authorization_id="auth-1",
            outpoint=self.outpoint,
            binding_id="binding-1",
            node_id="node-1",
            owner_key_id="owner-1",
            policy_id="policy-1",
            policy_version="1",
        )
        digest = compute_spend_request_hash(**values)
        self.request = SpendRequest(request_hash=digest, **values)
        self.decision = AuthorizationDecision(
            "PROTECTED", "approved", "b" * 64, "auth-1", self.outpoint
        )

    def test_protected_decision_submits_and_verifies_local_commit(self):
        result = consume_authorization(
            decision=self.decision, request=self.request, backend=self.backend
        )
        self.assertEqual(result.submission.state, SpendState.LOCAL_COMMITTED)
        self.assertEqual(result.evidence.commit_kind, CommitKind.LOCAL_ACID)
        self.assertEqual(self.backend.calls, 1)

    def test_standard_or_deny_cannot_spend(self):
        for mode in ("STANDARD", "DENY"):
            decision = AuthorizationDecision(mode, "not protected", "b" * 64)
            with self.assertRaises(UTXOBackendError):
                consume_authorization(
                    decision=decision, request=self.request, backend=self.backend
                )
        self.assertEqual(self.backend.calls, 0)

    def test_canonical_request_hash_is_checked_before_backend(self):
        invalid = SpendRequest(
            operation_id=self.request.operation_id,
            idempotency_key=self.request.idempotency_key,
            request_hash="c" * 64,
            operation_hash=self.request.operation_hash,
            authorization_id=self.request.authorization_id,
            outpoint=self.request.outpoint,
            binding_id=self.request.binding_id,
            node_id=self.request.node_id,
            owner_key_id=self.request.owner_key_id,
            policy_id=self.request.policy_id,
            policy_version=self.request.policy_version,
        )
        with self.assertRaises(UTXOBackendError):
            consume_authorization(
                decision=self.decision, request=invalid, backend=self.backend
            )
        self.assertEqual(self.backend.calls, 0)

    def test_operation_hash_mismatch_is_rejected(self):
        wrong = AuthorizationDecision(
            "PROTECTED", "approved", "d" * 64, "auth-1", self.outpoint
        )
        with self.assertRaises(UTXOBackendError):
            consume_authorization(
                decision=wrong, request=self.request, backend=self.backend
            )
        self.assertEqual(self.backend.calls, 0)


if __name__ == "__main__":
    unittest.main()
