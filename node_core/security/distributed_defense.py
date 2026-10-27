"""Signed security events, revocation snapshots, and quorum-gated containment primitives.

These are local verification primitives, not a distributed transport or consensus
implementation. Callers must supply trusted reporter keys and enforce verified
decisions at the protected service.
"""
from __future__ import annotations

from datetime import datetime, timezone
import base64
import hashlib
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from node_core.identity.node_identity import NodeIdentityStore


class SecurityRecordError(ValueError):
    """A signed security record is malformed, untrusted, stale, or invalid."""


def _canonical(record: dict[str, Any]) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise SecurityRecordError("Timestamp must include a timezone.")
    return parsed.astimezone(timezone.utc)


def create_signed_security_event(identity: NodeIdentityStore, *, event_type: str,
                                 subject_id: str, observed_at: datetime,
                                 expires_at: datetime, evidence_sha256: str,
                                 confidence: str = "observed") -> dict[str, Any]:
    """Create a signed, minimized event; it records an observation, not proven truth."""
    if not event_type or not subject_id:
        raise SecurityRecordError("event_type and subject_id are required.")
    if observed_at.tzinfo is None or expires_at.tzinfo is None or expires_at <= observed_at:
        raise SecurityRecordError("Event timestamps must be timezone-aware and expiry must follow observation.")
    if confidence not in {"observed", "corroborated", "confirmed"}:
        raise SecurityRecordError("Unsupported confidence level.")
    if len(evidence_sha256) != 64 or any(c not in "0123456789abcdef" for c in evidence_sha256):
        raise SecurityRecordError("evidence_sha256 must be a lowercase SHA-256 hex digest.")
    meta = identity.load()
    event = {
        "schema_version": 1,
        "record_type": "NODE_CORE_OS_SECURITY_EVENT",
        "reporter_node_id": meta["node_id"],
        "reporter_public_key": meta["public_key"],
        "event_type": event_type,
        "subject_id": subject_id,
        "observed_at": observed_at.astimezone(timezone.utc).isoformat(),
        "expires_at": expires_at.astimezone(timezone.utc).isoformat(),
        "evidence_sha256": evidence_sha256,
        "confidence": confidence,
    }
    event["signature"] = base64.b64encode(identity.sign(_canonical(event))).decode("ascii")
    return event


def verify_signed_security_event(event: dict[str, Any], trusted_reporter_keys: dict[str, str],
                                 *, now: datetime | None = None) -> bool:
    """Verify reporter authorization, signature, schema and event freshness."""
    try:
        if not isinstance(event, dict) or event.get("schema_version") != 1:
            return False
        if event.get("record_type") != "NODE_CORE_OS_SECURITY_EVENT":
            return False
        reporter_id = event["reporter_node_id"]
        public_hex = event["reporter_public_key"]
        if trusted_reporter_keys.get(reporter_id) != public_hex:
            return False
        public = bytes.fromhex(public_hex)
        if "sha256:" + hashlib.sha256(public).hexdigest() != reporter_id:
            return False
        signature = base64.b64decode(event["signature"], validate=True)
        unsigned = {k: v for k, v in event.items() if k != "signature"}
        Ed25519PublicKey.from_public_bytes(public).verify(signature, _canonical(unsigned))
        instant = now or datetime.now(timezone.utc)
        if instant.tzinfo is None:
            return False
        observed, expires = _utc(event["observed_at"]), _utc(event["expires_at"])
        if expires <= observed or instant.astimezone(timezone.utc) > expires:
            return False
        if event.get("confidence") not in {"observed", "corroborated", "confirmed"}:
            return False
        digest = event["evidence_sha256"]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            return False
        return True
    except (KeyError, TypeError, ValueError, InvalidSignature):
        return False


def create_signed_revocation_snapshot(identity: NodeIdentityStore, *, sequence: int,
                                      issued_at: datetime, expires_at: datetime,
                                      revoked_node_ids: list[str]) -> dict[str, Any]:
    """Create a monotonic-versioned signed revocation snapshot."""
    if sequence < 1 or issued_at.tzinfo is None or expires_at.tzinfo is None or expires_at <= issued_at:
        raise SecurityRecordError("Invalid sequence or revocation snapshot timestamps.")
    if any(not isinstance(item, str) or not item for item in revoked_node_ids):
        raise SecurityRecordError("Revoked node IDs must be non-empty strings.")
    if len(set(revoked_node_ids)) != len(revoked_node_ids):
        raise SecurityRecordError("Duplicate revoked node IDs are not allowed.")
    meta = identity.load()
    snapshot = {
        "schema_version": 1,
        "record_type": "NODE_CORE_OS_REVOCATION_SNAPSHOT",
        "issuer_node_id": meta["node_id"],
        "issuer_public_key": meta["public_key"],
        "sequence": sequence,
        "issued_at": issued_at.astimezone(timezone.utc).isoformat(),
        "expires_at": expires_at.astimezone(timezone.utc).isoformat(),
        "revoked_node_ids": sorted(revoked_node_ids),
    }
    snapshot["signature"] = base64.b64encode(identity.sign(_canonical(snapshot))).decode("ascii")
    return snapshot


def verify_revocation_snapshot(snapshot: dict[str, Any], trusted_issuer_keys: dict[str, str],
                               *, last_sequence: int, now: datetime | None = None) -> bool:
    """Verify signature, issuer allowlist, freshness and anti-rollback sequence."""
    try:
        if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1:
            return False
        if snapshot.get("record_type") != "NODE_CORE_OS_REVOCATION_SNAPSHOT":
            return False
        issuer_id, public_hex = snapshot["issuer_node_id"], snapshot["issuer_public_key"]
        if trusted_issuer_keys.get(issuer_id) != public_hex:
            return False
        public = bytes.fromhex(public_hex)
        if "sha256:" + hashlib.sha256(public).hexdigest() != issuer_id:
            return False
        Ed25519PublicKey.from_public_bytes(public).verify(
            base64.b64decode(snapshot["signature"], validate=True),
            _canonical({k: v for k, v in snapshot.items() if k != "signature"}),
        )
        instant = now or datetime.now(timezone.utc)
        if instant.tzinfo is None or int(snapshot["sequence"]) <= last_sequence:
            return False
        issued, expires = _utc(snapshot["issued_at"]), _utc(snapshot["expires_at"])
        if issued > instant.astimezone(timezone.utc) or expires <= instant.astimezone(timezone.utc) or expires <= issued:
            return False
        revoked = snapshot["revoked_node_ids"]
        return isinstance(revoked, list) and all(isinstance(x, str) and x for x in revoked) and len(set(revoked)) == len(revoked)
    except (KeyError, TypeError, ValueError, InvalidSignature):
        return False


def should_quarantine(subject_id: str, verified_events: list[dict[str, Any]],
                      *, minimum_independent_reporters: int = 3) -> bool:
    """Require corroboration by distinct verified reporters; never trust one report."""
    if not subject_id or minimum_independent_reporters < 2:
        raise SecurityRecordError("Quarantine requires at least two independent reporters.")
    reporters = {
        item.get("reporter_node_id")
        for item in verified_events
        if item.get("subject_id") == subject_id
        and item.get("confidence") in {"corroborated", "confirmed"}
        and item.get("verified") is True
        and isinstance(item.get("reporter_node_id"), str)
    }
    return len(reporters) >= minimum_independent_reporters
