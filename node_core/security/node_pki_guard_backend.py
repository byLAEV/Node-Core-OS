"""Shared abstract backend contract for NODE-PKI-GUARD v1.2.

The contract separates protocol/security logic from persistence. Standalone
SQLite commits and NODE Core OS Network finality are represented as different
commit kinds and must never be reported interchangeably.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import re
import hashlib
import json
from typing import Any, Mapping


HEX_32 = re.compile(r"^[0-9a-f]{64}$")
SPEND_REQUEST_DOMAIN = "NODE-PKI-GUARD-SPEND-REQUEST-v1"
OUTPOINT_RE = re.compile(r"^([0-9a-f]{64}):([0-9]{1,10})$")


def compute_spend_request_hash(
    *,
    operation_id: str,
    idempotency_key: str,
    operation_hash: str,
    authorization_id: str,
    outpoint: str,
    binding_id: str,
    node_id: str,
    owner_key_id: str,
    policy_id: str,
    policy_version: str,
    fee_amount: int = 0,
    fee_asset: str = "NONE",
) -> str:
    """Compute the domain-separated digest for every immutable spend field."""
    payload = {
        "domain": SPEND_REQUEST_DOMAIN,
        "operation_id": operation_id,
        "idempotency_key": idempotency_key,
        "operation_hash": operation_hash,
        "authorization_id": authorization_id,
        "outpoint": outpoint,
        "binding_id": binding_id,
        "node_id": node_id,
        "owner_key_id": owner_key_id,
        "policy_id": policy_id,
        "policy_version": policy_version,
        "fee_amount": fee_amount,
        "fee_asset": fee_asset,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class BackendContractError(RuntimeError):
    """Raised when a backend request or response violates the shared contract."""


class IdempotencyConflict(BackendContractError):
    """An idempotency key was reused with different request content."""


class CommitOutcomeUnknown(BackendContractError):
    """A commit outcome could not be established; callers must reconcile."""


class UTXOStatus(str, Enum):
    UNSPENT = "UNSPENT"
    SPENT = "SPENT"
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN = "UNKNOWN"


class SpendState(str, Enum):
    SUBMITTED = "SUBMITTED"
    PENDING_FINALITY = "PENDING_FINALITY"
    LOCAL_COMMITTED = "LOCAL_COMMITTED"
    NETWORK_FINALIZED = "NETWORK_FINALIZED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class CommitKind(str, Enum):
    LOCAL_ACID = "LOCAL_ACID"
    NETWORK_CONSENSUS = "NETWORK_CONSENSUS"


@dataclass(frozen=True)
class AuthorizationUTXO:
    """Authorization data accepted into a backend after issuer verification."""

    outpoint: str
    authorization_id: str
    binding_id: str
    node_id: str
    owner_key_id: str
    operation_hash: str
    policy_id: str
    policy_version: str

    def __post_init__(self) -> None:
        match = OUTPOINT_RE.fullmatch(self.outpoint) if isinstance(self.outpoint, str) else None
        if match is None:
            raise ValueError("outpoint must use canonical lowercase txid:vout form")
        for name in (
            "authorization_id", "binding_id", "node_id", "owner_key_id",
            "policy_id", "policy_version",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(name + " is required")
        if not HEX_32.fullmatch(self.operation_hash):
            raise ValueError("operation_hash must be a lowercase SHA-256 digest")


@dataclass(frozen=True)
class SpendRequest:
    """Immutable request to consume one authorization capability."""

    operation_id: str
    idempotency_key: str
    request_hash: str
    operation_hash: str
    authorization_id: str
    outpoint: str
    binding_id: str
    node_id: str
    owner_key_id: str
    policy_id: str
    policy_version: str
    fee_amount: int = 0
    fee_asset: str = "NONE"

    def __post_init__(self) -> None:
        for name in (
            "operation_id", "idempotency_key", "authorization_id", "outpoint",
            "binding_id", "node_id", "owner_key_id", "policy_id", "policy_version",
            "fee_asset",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(name + " is required")
        if not HEX_32.fullmatch(self.request_hash):
            raise ValueError("request_hash must be a lowercase SHA-256 digest")
        if not HEX_32.fullmatch(self.operation_hash):
            raise ValueError("operation_hash must be a lowercase SHA-256 digest")
        if OUTPOINT_RE.fullmatch(self.outpoint) is None:
            raise ValueError("outpoint must use canonical lowercase txid:vout form")
        if type(self.fee_amount) is not int or self.fee_amount < 0:
            raise ValueError("fee_amount must be a non-negative integer")



@dataclass(frozen=True)
class SpendSubmission:
    transaction_id: str
    request_hash: str
    outpoint: str
    operation_id: str
    idempotency_key: str
    operation_hash: str
    authorization_id: str
    state: SpendState
    fee_charged: int = 0


@dataclass(frozen=True)
class CommitEvidence:
    transaction_id: str
    commit_kind: CommitKind
    backend_id: str
    committed_at_utc: str
    sequence: int
    evidence_hash: str
    external_proof: Mapping[str, Any] = field(default_factory=dict)


class UTXOAuthorizationBackend(ABC):
    """Abstract strategy shared by Standalone and Network implementations.

    register_authorization is an issuer boundary: implementations MUST only
    accept records after the calling service has validated the authorization
    format, issuer signature, binding, policy and ownership proof.
    """

    @abstractmethod
    def register_authorization(self, authorization: AuthorizationUTXO) -> None:
        """Register a newly issued, verified, unspent authorization output."""

    @abstractmethod
    def get_utxo_status(self, outpoint: str) -> UTXOStatus:
        """Return the authoritative status of one canonical outpoint."""

    @abstractmethod
    def get_authorization(self, outpoint: str) -> AuthorizationUTXO | None:
        """Return immutable authorization metadata for an outpoint, if known."""

    @abstractmethod
    def get_idempotent_result(self, idempotency_key: str) -> SpendSubmission | None:
        """Return the durable result for a globally unique idempotency key."""

    @abstractmethod
    def submit_spend_atomic(self, request: SpendRequest) -> SpendSubmission:
        """Atomically validate request ownership and consume an unspent outpoint."""

    @abstractmethod
    def wait_for_commit(
        self, transaction_id: str, timeout_seconds: float
    ) -> CommitEvidence:
        """Wait for this backend's commit condition (local ACID or network finality)."""

    @abstractmethod
    def verify_commit_evidence(
        self, evidence: CommitEvidence, transaction_id: str
    ) -> bool:
        """Verify evidence according to the backend's declared CommitKind."""
