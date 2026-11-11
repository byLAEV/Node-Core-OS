"""Shared UTXO spend coordinator for NODE-PKI-GUARD.

This module delegates persistence and commit guarantees to the injected backend.
It does not implement or emulate a ledger, consensus, or network finality.
"""
from __future__ import annotations

from dataclasses import dataclass

from node_core.security.node_pki_guard import AuthorizationDecision, NodePKIGuardError
from node_core.security.node_pki_guard_backend import (
    BackendContractError,
    CommitEvidence,
    CommitKind,
    IdempotencyConflict,
    SpendRequest,
    SpendState,
    SpendSubmission,
    UTXOAuthorizationBackend,
)


class UTXOBackendError(NodePKIGuardError):
    """Backend failure while submitting or reconciling an authorization spend."""


@dataclass(frozen=True)
class FinalizedAuthorization:
    submission: SpendSubmission
    evidence: CommitEvidence


def consume_authorization(
    *,
    decision: AuthorizationDecision,
    request: SpendRequest,
    backend: UTXOAuthorizationBackend,
    finality_timeout_seconds: float = 60.0,
) -> FinalizedAuthorization:
    """Consume only a PROTECTED decision and verify backend-specific commit evidence.

    For Standalone this proves a local ACID commit, not distributed finality.
    For Network this can return only after the concrete adapter verifies its
    consensus proof. A protected external executor must run after this returns.
    """
    if decision.decision != "PROTECTED":
        raise UTXOBackendError("Only a PROTECTED decision may submit a UTXO spend")
    if decision.operation_hash != request.operation_hash:
        raise UTXOBackendError("Operation hash does not match policy decision")
    if decision.authorization_id != request.authorization_id:
        raise UTXOBackendError("Authorization ID does not match policy decision")
    if decision.outpoint != request.outpoint:
        raise UTXOBackendError("Outpoint does not match policy decision")
    if not 0 < finality_timeout_seconds <= 3600:
        raise ValueError("finality_timeout_seconds must be greater than 0 and at most 3600")

    try:
        previous = backend.get_idempotent_result(request.idempotency_key)
        if previous is not None:
            if (
                previous.operation_id != request.operation_id
                or previous.request_hash != request.request_hash
                or previous.operation_hash != request.operation_hash
                or previous.outpoint != request.outpoint
                or previous.authorization_id != request.authorization_id
            ):
                raise IdempotencyConflict(
                    "Idempotency key is already bound to different request content"
                )
            submission = previous
        else:
            submission = backend.submit_spend_atomic(request)

        if (
            submission.operation_id != request.operation_id
            or submission.request_hash != request.request_hash
            or submission.operation_hash != request.operation_hash
            or submission.outpoint != request.outpoint
            or submission.authorization_id != request.authorization_id
        ):
            raise UTXOBackendError("Backend returned a result inconsistent with the spend request")

        if submission.state not in {
            SpendState.SUBMITTED,
            SpendState.PENDING_FINALITY,
            SpendState.LOCAL_COMMITTED,
            SpendState.NETWORK_FINALIZED,
        }:
            raise UTXOBackendError("Backend did not accept the authorization spend")

        evidence = backend.wait_for_commit(
            submission.transaction_id, finality_timeout_seconds
        )
        if evidence.transaction_id != submission.transaction_id:
            raise UTXOBackendError("Commit evidence refers to a different transaction")
        if not backend.verify_commit_evidence(evidence, submission.transaction_id):
            raise UTXOBackendError("Backend commit evidence verification failed")

        if evidence.commit_kind is CommitKind.LOCAL_ACID:
            if submission.state is not SpendState.LOCAL_COMMITTED:
                raise UTXOBackendError("Local ACID evidence does not match submission state")
        elif evidence.commit_kind is CommitKind.NETWORK_CONSENSUS:
            if submission.state not in {
                SpendState.PENDING_FINALITY, SpendState.NETWORK_FINALIZED
            }:
                raise UTXOBackendError("Network finality evidence does not match submission state")
        else:
            raise UTXOBackendError("Unsupported backend commit evidence kind")

        return FinalizedAuthorization(submission=submission, evidence=evidence)
    except (BackendContractError, TimeoutError) as exc:
        raise UTXOBackendError(str(exc)) from exc
