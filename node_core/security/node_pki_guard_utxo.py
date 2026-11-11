"""Contract and orchestration boundary for NODE-PKI-GUARD UTXO consumption.

A backend implementation must provide atomic outpoint consumption and durable
idempotency. This module does not implement a ledger or claim distributed
consensus. It only coordinates a backend that supplies those guarantees.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from node_core.security.node_pki_guard import AuthorizationDecision, NodePKIGuardError


class UTXOBackendError(NodePKIGuardError):
    """Backend failure while submitting or reconciling an authorization spend."""


@dataclass(frozen=True)
class SpendRequest:
    operation_id: str
    idempotency_key: str
    operation_hash: str
    authorization_id: str
    outpoint: str
    binding_id: str
    policy_id: str
    policy_version: str

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if not isinstance(value, str) or not value:
                raise ValueError(name + " is required")


@dataclass(frozen=True)
class SpendSubmission:
    transaction_id: str
    outpoint: str
    operation_id: str
    operation_hash: str
    state: str


@dataclass(frozen=True)
class FinalityProof:
    transaction_id: str
    block_id: str
    finalized_height: int
    proof_format: str
    proof_data: Mapping[str, Any]


@dataclass(frozen=True)
class FinalizedAuthorization:
    submission: SpendSubmission
    finality: FinalityProof


class UTXOAuthorizationBackend(Protocol):
    """Required contract for a real, authoritative UTXO backend.

    submit_spend_atomic MUST atomically validate and consume the outpoint,
    reject concurrent double spends, and durably bind the idempotency key to
    the request hash. Repeated identical requests MUST return the same result.
    Reusing an idempotency key with different content MUST raise a conflict.
    """

    def get_idempotent_result(self, idempotency_key: str) -> SpendSubmission | None:
        """Return the durable result for a previously accepted request."""

    def submit_spend_atomic(self, request: SpendRequest) -> SpendSubmission:
        """Atomically consume the outpoint and persist the idempotency mapping."""

    def wait_for_finality(self, transaction_id: str, timeout_seconds: float) -> FinalityProof:
        """Wait until the transaction reaches the backend's documented finality."""

    def verify_finality_proof(self, proof: FinalityProof, transaction_id: str) -> bool:
        """Independently verify that proof finalizes the specified transaction."""


def consume_authorization(
    *,
    decision: AuthorizationDecision,
    request: SpendRequest,
    backend: UTXOAuthorizationBackend,
    finality_timeout_seconds: float = 60.0,
) -> FinalizedAuthorization:
    """Submit a PROTECTED authorization spend and require verified finality.

    This function does not execute the protected external operation. The caller
    may invoke its idempotent executor only after this function returns.
    """
    if decision.decision != "PROTECTED":
        raise UTXOBackendError("Only a PROTECTED decision may submit a UTXO spend")
    if decision.operation_hash != request.operation_hash:
        raise UTXOBackendError("Spend request operation hash does not match policy decision")
    if decision.authorization_id != request.authorization_id:
        raise UTXOBackendError("Spend request authorization ID does not match policy decision")
    if decision.outpoint != request.outpoint:
        raise UTXOBackendError("Spend request outpoint does not match policy decision")
    if finality_timeout_seconds <= 0 or finality_timeout_seconds > 3600:
        raise ValueError("finality_timeout_seconds must be greater than 0 and at most 3600")

    previous = backend.get_idempotent_result(request.idempotency_key)
    if previous is not None:
        if (
            previous.operation_id != request.operation_id
            or previous.operation_hash != request.operation_hash
            or previous.outpoint != request.outpoint
        ):
            raise UTXOBackendError("Idempotency key is already bound to different request content")
        submission = previous
    else:
        submission = backend.submit_spend_atomic(request)

    if (
        submission.operation_id != request.operation_id
        or submission.operation_hash != request.operation_hash
        or submission.outpoint != request.outpoint
        or not submission.transaction_id
    ):
        raise UTXOBackendError("Backend returned a spend result inconsistent with the request")

    if submission.state not in {"SUBMITTED", "FINALIZED"}:
        raise UTXOBackendError("Backend did not accept the authorization spend")

    proof = backend.wait_for_finality(submission.transaction_id, finality_timeout_seconds)
    if proof.transaction_id != submission.transaction_id:
        raise UTXOBackendError("Finality proof refers to a different transaction")
    if proof.finalized_height < 0 or not proof.block_id or not proof.proof_format:
        raise UTXOBackendError("Finality proof is incomplete")
    if not backend.verify_finality_proof(proof, submission.transaction_id):
        raise UTXOBackendError("Backend finality proof verification failed")

    finalized_submission = SpendSubmission(
        transaction_id=submission.transaction_id,
        outpoint=submission.outpoint,
        operation_id=submission.operation_id,
        operation_hash=submission.operation_hash,
        state="FINALIZED",
    )
    return FinalizedAuthorization(finalized_submission, proof)
