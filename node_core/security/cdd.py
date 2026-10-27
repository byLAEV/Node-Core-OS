"""Local primitives for the experimental CID Distributed Defense (CDD) MVP.

This module verifies signed policy manifests and enforces a bounded, in-process
sliding-window limiter. It is not yet an HTTP gateway, IPFS publisher, P2P
transport, distributed quota coordinator, or DDoS mitigation network.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import base64
import hashlib
import json
import threading
import time
from typing import Any, Callable, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from node_core.identity.node_identity import NodeIdentityStore


SCHEMA_VERSION = 1
RECORD_TYPE = "NODE_CORE_OS_CDD_POLICY"
MAX_REQUESTS = 100_000
MAX_WINDOW_SECONDS = 3_600
MAX_BODY_BYTES = 1_048_576
MAX_TRACKED_CLIENTS = 4_096

_POLICY_KEYS = {
    "schema_version",
    "record_type",
    "issuer_node_id",
    "issuer_public_key",
    "service_id",
    "sequence",
    "issued_at",
    "expires_at",
    "limits",
    "origin_id",
}
_LIMIT_KEYS = {"max_requests", "window_seconds", "max_body_bytes"}


class CDDPolicyError(ValueError):
    """A CDD policy is malformed or has invalid configuration."""


def canonical_json(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes for signing and verification."""
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise CDDPolicyError("Policy cannot be represented as canonical JSON.") from exc


def _timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise CDDPolicyError("Policy timestamps must be timezone-aware.")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise CDDPolicyError("Policy timestamp is missing or invalid.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CDDPolicyError("Policy timestamp is invalid.") from exc
    if parsed.tzinfo is None:
        raise CDDPolicyError("Policy timestamp must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _positive_integer(value: Any, name: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise CDDPolicyError(f"{name} must be an integer between 1 and {maximum}.")
    return value


def _validate_body(body: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(body, Mapping) or set(body) != _POLICY_KEYS:
        raise CDDPolicyError("Policy fields do not match the required schema.")
    if body["schema_version"] != SCHEMA_VERSION or body["record_type"] != RECORD_TYPE:
        raise CDDPolicyError("Unsupported CDD policy schema or record type.")

    issuer_id = body["issuer_node_id"]
    public_hex = body["issuer_public_key"]
    if not isinstance(issuer_id, str) or not issuer_id.startswith("sha256:") or len(issuer_id) != 71:
        raise CDDPolicyError("Issuer node ID is invalid.")
    if not isinstance(public_hex, str) or len(public_hex) != 64:
        raise CDDPolicyError("Issuer public key must be 32-byte hexadecimal.")
    try:
        public_bytes = bytes.fromhex(public_hex)
    except ValueError as exc:
        raise CDDPolicyError("Issuer public key must be hexadecimal.") from exc
    if "sha256:" + hashlib.sha256(public_bytes).hexdigest() != issuer_id:
        raise CDDPolicyError("Issuer node ID does not match its public key.")

    for field in ("service_id", "origin_id"):
        value = body[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 256:
            raise CDDPolicyError(f"{field} must be a non-empty string of at most 256 characters.")

    _positive_integer(body["sequence"], "sequence", 2**63 - 1)
    issued_at = _parse_timestamp(body["issued_at"])
    expires_at = _parse_timestamp(body["expires_at"])
    if expires_at <= issued_at:
        raise CDDPolicyError("Policy expiry must follow its issue time.")

    limits = body["limits"]
    if not isinstance(limits, Mapping) or set(limits) != _LIMIT_KEYS:
        raise CDDPolicyError("Policy limits do not match the required schema.")
    _positive_integer(limits["max_requests"], "max_requests", MAX_REQUESTS)
    _positive_integer(limits["window_seconds"], "window_seconds", MAX_WINDOW_SECONDS)
    _positive_integer(limits["max_body_bytes"], "max_body_bytes", MAX_BODY_BYTES)
    return dict(body)


def create_signed_policy(
    identity: NodeIdentityStore,
    *,
    service_id: str,
    sequence: int,
    issued_at: datetime,
    expires_at: datetime,
    max_requests: int,
    window_seconds: int,
    max_body_bytes: int,
    origin_id: str,
) -> dict[str, Any]:
    """Create a policy signed by an existing Node Core OS Ed25519 identity."""
    metadata = identity.load()
    body = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "issuer_node_id": metadata["node_id"],
        "issuer_public_key": metadata["public_key"],
        "service_id": service_id,
        "sequence": sequence,
        "issued_at": _timestamp(issued_at),
        "expires_at": _timestamp(expires_at),
        "limits": {
            "max_requests": max_requests,
            "window_seconds": window_seconds,
            "max_body_bytes": max_body_bytes,
        },
        "origin_id": origin_id,
    }
    _validate_body(body)
    signature = identity.sign(canonical_json(body))
    return {**body, "signature": base64.b64encode(signature).decode("ascii")}


def verify_signed_policy(
    policy: Mapping[str, Any],
    trusted_issuer_keys: Mapping[str, str],
    *,
    last_sequence: int = 0,
    now: datetime | None = None,
) -> bool:
    """Fail closed on unknown issuer, invalid signature, expiry, or rollback."""
    try:
        if not isinstance(policy, Mapping) or set(policy) != _POLICY_KEYS | {"signature"}:
            return False
        body = {key: value for key, value in policy.items() if key != "signature"}
        _validate_body(body)
        issuer_id = body["issuer_node_id"]
        public_hex = body["issuer_public_key"]
        if trusted_issuer_keys.get(issuer_id) != public_hex:
            return False
        if isinstance(last_sequence, bool) or not isinstance(last_sequence, int) or last_sequence < 0:
            return False
        if body["sequence"] <= last_sequence:
            return False
        instant = now or datetime.now(timezone.utc)
        if not isinstance(instant, datetime) or instant.tzinfo is None:
            return False
        current = instant.astimezone(timezone.utc)
        if _parse_timestamp(body["issued_at"]) > current:
            return False
        if _parse_timestamp(body["expires_at"]) <= current:
            return False
        signature_text = policy["signature"]
        if not isinstance(signature_text, str):
            return False
        signature = base64.b64decode(signature_text, validate=True)
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex))
        public_key.verify(signature, canonical_json(body))
        return True
    except (CDDPolicyError, KeyError, TypeError, ValueError, InvalidSignature):
        return False


class SlidingWindowRateLimiter:
    """Bounded local rate limiter; it does not coordinate quotas across nodes."""

    def __init__(
        self,
        *,
        max_tracked_clients: int = MAX_TRACKED_CLIENTS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if (
            isinstance(max_tracked_clients, bool)
            or not isinstance(max_tracked_clients, int)
            or max_tracked_clients < 1
        ):
            raise ValueError("max_tracked_clients must be a positive integer.")
        self._max_tracked_clients = max_tracked_clients
        self._clock = clock
        self._events: dict[tuple[str, str], deque[float]] = {}
        self._windows: dict[tuple[str, str], int] = {}
        self._lock = threading.Lock()

    def allow(
        self,
        client_id: str,
        route: str,
        *,
        max_requests: int,
        window_seconds: int,
        now: float | None = None,
    ) -> bool:
        """Return whether the request is inside the configured local quota.

        Unknown clients are denied when the bounded tracking table is full.
        Callers must supply an authenticated or otherwise policy-approved client
        identifier; a user-controlled header alone is not a trusted identity.
        """
        if not isinstance(client_id, str) or not client_id or len(client_id) > 256:
            return False
        if not isinstance(route, str) or not route.startswith("/") or len(route) > 2048:
            return False
        try:
            _positive_integer(max_requests, "max_requests", MAX_REQUESTS)
            _positive_integer(window_seconds, "window_seconds", MAX_WINDOW_SECONDS)
        except CDDPolicyError:
            return False

        instant = self._clock() if now is None else now
        if isinstance(instant, bool) or not isinstance(instant, (int, float)):
            return False
        key = (client_id, route)
        with self._lock:
            for existing_key in list(self._events):
                window = self._windows[existing_key]
                queue = self._events[existing_key]
                cutoff = instant - window
                while queue and queue[0] <= cutoff:
                    queue.popleft()
                if not queue:
                    del self._events[existing_key]
                    del self._windows[existing_key]

            if key not in self._events:
                if len(self._events) >= self._max_tracked_clients:
                    return False
                self._events[key] = deque()
                self._windows[key] = window_seconds
            queue = self._events[key]
            cutoff = instant - window_seconds
            while queue and queue[0] <= cutoff:
                queue.popleft()
            self._windows[key] = window_seconds
            if len(queue) >= max_requests:
                return False
            queue.append(float(instant))
            return True
