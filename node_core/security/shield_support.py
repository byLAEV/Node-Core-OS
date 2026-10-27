"""Quorum-backed Shield support evidence bundles.

A support certificate is a portable proof bundle made from independently signed
security events. It is not an X.509 certificate, a global ban, or proof that
reporter keys belong to independent operators. Every receiver must verify it
against its own trusted-reporter policy before applying local mitigation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from node_core.security.distributed_defense import (
    SecurityRecordError,
    should_quarantine,
    verify_signed_security_event,
)


def create_shield_support_certificate(
    subject_id: str,
    events: list[dict[str, Any]],
    trusted_reporter_keys: dict[str, str],
    *,
    minimum_independent_reporters: int = 3,
    now: datetime | None = None,
    lifetime: timedelta = timedelta(minutes=5),
) -> dict[str, Any]:
    """Build a short-lived evidence bundle only after the local quorum is met."""
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None or not subject_id:
        raise SecurityRecordError("A subject and timezone-aware current time are required.")
    if minimum_independent_reporters < 2 or lifetime <= timedelta(0):
        raise SecurityRecordError("Invalid quorum threshold or certificate lifetime.")

    valid_events = [
        event for event in events
        if isinstance(event, dict)
        and event.get("subject_id") == subject_id
        and event.get("confidence") in {"corroborated", "confirmed"}
        and verify_signed_security_event(event, trusted_reporter_keys, now=instant)
    ]
    if not should_quarantine(
        subject_id,
        valid_events,
        trusted_reporter_keys,
        minimum_independent_reporters=minimum_independent_reporters,
        now=instant,
    ):
        raise SecurityRecordError("Insufficient valid independent reporter quorum.")

    event_expiries = [
        datetime.fromisoformat(event["expires_at"].replace("Z", "+00:00"))
        for event in valid_events
    ]
    expiry = min(instant + lifetime, *(event_expiries))
    return {
        "schema_version": 1,
        "record_type": "NODE_CORE_OS_SHIELD_SUPPORT_CERTIFICATE",
        "subject_id": subject_id,
        "issued_at": instant.astimezone(timezone.utc).isoformat(),
        "expires_at": expiry.astimezone(timezone.utc).isoformat(),
        "minimum_independent_reporters": minimum_independent_reporters,
        "events": valid_events,
    }


def verify_shield_support_certificate(
    certificate: dict[str, Any],
    trusted_reporter_keys: dict[str, str],
    *,
    minimum_required_reporters: int = 3,
    now: datetime | None = None,
) -> bool:
    """Verify the evidence bundle using receiver-owned trust and quorum policy."""
    try:
        if not isinstance(certificate, dict):
            return False
        if certificate.get("schema_version") != 1:
            return False
        if certificate.get("record_type") != "NODE_CORE_OS_SHIELD_SUPPORT_CERTIFICATE":
            return False
        subject_id = certificate["subject_id"]
        issued_at = datetime.fromisoformat(certificate["issued_at"].replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(certificate["expires_at"].replace("Z", "+00:00"))
        instant = now or datetime.now(timezone.utc)
        if not subject_id or instant.tzinfo is None:
            return False
        current = instant.astimezone(timezone.utc)
        if issued_at.tzinfo is None or expires_at.tzinfo is None:
            return False
        if issued_at > current or expires_at <= current or expires_at <= issued_at:
            return False
        claimed_threshold = certificate["minimum_independent_reporters"]
        if not isinstance(claimed_threshold, int) or isinstance(claimed_threshold, bool):
            return False
        if minimum_required_reporters < 2 or claimed_threshold < minimum_required_reporters:
            return False
        events = certificate["events"]
        if not isinstance(events, list):
            return False
        # Do not let a bundle extend the lifetime of any underlying signed event.
        for event in events:
            if not isinstance(event, dict) or event.get("subject_id") != subject_id:
                return False
            event_expiry = datetime.fromisoformat(event["expires_at"].replace("Z", "+00:00"))
            if event_expiry.tzinfo is None or expires_at > event_expiry:
                return False
        return should_quarantine(
            subject_id,
            events,
            trusted_reporter_keys,
            minimum_independent_reporters=minimum_required_reporters,
            now=current,
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
