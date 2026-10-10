"""Validation helpers for the planned Node Core identity function proof.

This module validates record structure and time semantics only. It does not
verify cryptographic signatures, identity ownership, network propagation, or
consensus finality.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping


SUPPORTED_SCHEMA = "node-core.identity-function-evidence"
SUPPORTED_SCHEMA_VERSION = "0.1.0"

_REQUIRED_ACTIVITY_FIELDS = (
    "protocol_id",
    "poll_id",
    "period_id",
    "activity_type",
)
_REQUIRED_TIMESTAMP_FIELDS = ("created_at", "valid_from", "valid_until")
_REQUIRED_VALIDATION_FIELDS = ("policy_version", "status", "checks")


class EvidenceValidationError(ValueError):
    """Raised when an evidence record does not satisfy the local contract."""


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EvidenceValidationError(f"{field} must be a JSON object.")
    return value


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceValidationError(f"{field} must be a non-empty string.")
    return value.strip()


def _parse_timestamp(value: Any, field: str) -> datetime:
    text = _require_non_empty_string(value, field)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise EvidenceValidationError(
            f"{field} must be an ISO 8601 timestamp."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceValidationError(
            f"{field} must include a timezone or UTC offset."
        )
    return parsed.astimezone(timezone.utc)


def validate_evidence_record(record: Mapping[str, Any]) -> None:
    """Validate required fields and timestamp relationships.

    Signature and identity verification are intentionally out of scope for this
    first local validation step. Callers must not treat this function alone as
    proof that the record is authentic or accepted by the network.
    """
    data = _require_mapping(record, "record")

    if data.get("schema") != SUPPORTED_SCHEMA:
        raise EvidenceValidationError("Unsupported evidence schema.")
    if data.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise EvidenceValidationError("Unsupported evidence schema version.")

    _require_non_empty_string(data.get("evidence_id"), "evidence_id")
    _require_non_empty_string(data.get("identity_ref"), "identity_ref")

    activity = _require_mapping(data.get("activity"), "activity")
    for field in _REQUIRED_ACTIVITY_FIELDS:
        _require_non_empty_string(activity.get(field), f"activity.{field}")

    timestamps = _require_mapping(data.get("timestamps"), "timestamps")
    parsed_timestamps = {
        field: _parse_timestamp(timestamps.get(field), f"timestamps.{field}")
        for field in _REQUIRED_TIMESTAMP_FIELDS
    }
    if parsed_timestamps["valid_until"] <= parsed_timestamps["valid_from"]:
        raise EvidenceValidationError(
            "timestamps.valid_until must be later than timestamps.valid_from."
        )
    if parsed_timestamps["created_at"] < parsed_timestamps["valid_from"]:
        raise EvidenceValidationError(
            "timestamps.created_at cannot be earlier than timestamps.valid_from."
        )

    validation = _require_mapping(data.get("validation"), "validation")
    for field in _REQUIRED_VALIDATION_FIELDS:
        if field not in validation:
            raise EvidenceValidationError(f"validation.{field} is required.")
    _require_non_empty_string(validation.get("policy_version"), "validation.policy_version")
    _require_non_empty_string(validation.get("status"), "validation.status")
    checks = validation.get("checks")
    if not isinstance(checks, list) or any(
        not isinstance(item, str) or not item.strip() for item in checks
    ):
        raise EvidenceValidationError(
            "validation.checks must be a list of non-empty strings."
        )

    content = _require_mapping(data.get("content"), "content")
    cid = content.get("cid")
    if cid is not None:
        _require_non_empty_string(cid, "content.cid")
    previous_ref = content.get("previous_evidence_ref")
    if previous_ref is not None:
        _require_non_empty_string(
            previous_ref, "content.previous_evidence_ref"
        )

    signature = _require_mapping(data.get("signature"), "signature")
    _require_non_empty_string(signature.get("algorithm"), "signature.algorithm")
    _require_non_empty_string(signature.get("value"), "signature.value")


def derive_evidence_status(
    record: Mapping[str, Any],
    *,
    now: datetime | None = None,
    renewal_window: timedelta = timedelta(0),
    grace_period: timedelta = timedelta(0),
) -> str:
    """Derive evidence freshness from timestamps and policy durations.

    The returned status is a local time-based assessment, not a consensus
    decision. A caller should persist or publish it only with the policy and
    observation time that produced it.
    """
    validate_evidence_record(record)

    if renewal_window < timedelta(0) or grace_period < timedelta(0):
        raise ValueError("renewal_window and grace_period cannot be negative.")

    observed_at = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("now must include a timezone or UTC offset.")
    observed_at = observed_at.astimezone(timezone.utc)

    timestamps = record["timestamps"]
    valid_from = _parse_timestamp(timestamps["valid_from"], "timestamps.valid_from")
    valid_until = _parse_timestamp(timestamps["valid_until"], "timestamps.valid_until")

    if observed_at < valid_from:
        return "verification_pending"
    if observed_at < valid_until - renewal_window:
        return "current"
    if observed_at < valid_until:
        return "renewal_due"
    if observed_at < valid_until + grace_period:
        return "grace"
    return "expired"
