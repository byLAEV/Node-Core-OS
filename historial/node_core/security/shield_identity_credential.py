"""Quorum-signed identity credentials for Node Core OS Shield services/devices.

These JSON credentials are not browser-trusted X.509 certificates. They bind an
Ed25519 subject key to a type, scope and validity interval, with signatures from
a locally trusted quorum of Node Core OS identity nodes. Distribution and issuer
enrollment remain deployment responsibilities.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import base64
import hashlib
import json
from typing import Any, Iterable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from node_core.identity.node_identity import NodeIdentityStore
from node_core.security.distributed_defense import SecurityRecordError


_ALLOWED_SUBJECT_TYPES = {
    "web_application",
    "service",
    "server",
    "database",
    "device",
    "host",
}
_MAX_LIFETIME = timedelta(days=90)


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _public_key_bytes(public_key_hex: str) -> bytes:
    try:
        raw = bytes.fromhex(public_key_hex)
        Ed25519PublicKey.from_public_bytes(raw)
        if len(raw) != 32:
            raise ValueError("wrong key length")
        return raw
    except (TypeError, ValueError) as exc:
        raise SecurityRecordError("Subject public key must be a valid Ed25519 public key.") from exc


def _node_id(public_key_bytes: bytes) -> str:
    return "sha256:" + hashlib.sha256(public_key_bytes).hexdigest()


def create_quorum_identity_credential(
    *,
    subject_public_key_hex: str,
    subject_type: str,
    scopes: Iterable[str],
    issuer_stores: Iterable[NodeIdentityStore],
    minimum_issuers: int = 3,
    now: datetime | None = None,
    lifetime: timedelta = timedelta(days=30),
) -> dict[str, Any]:
    """Issue a credential signed by a quorum of distinct issuer node identities."""
    instant = now or datetime.now(timezone.utc)
    issuers = list(issuer_stores)
    normalized_scopes = sorted(set(scopes))
    raw_subject = _public_key_bytes(subject_public_key_hex)

    if instant.tzinfo is None:
        raise SecurityRecordError("Issuance time must include a timezone.")
    if subject_type not in _ALLOWED_SUBJECT_TYPES:
        raise SecurityRecordError("Unsupported subject type.")
    if not normalized_scopes or any(
        not isinstance(scope, str) or not scope.strip() or len(scope) > 128
        for scope in normalized_scopes
    ):
        raise SecurityRecordError("At least one valid, bounded scope is required.")
    if minimum_issuers < 2 or len(issuers) < minimum_issuers:
        raise SecurityRecordError("Not enough issuer nodes to satisfy the quorum.")
    if lifetime <= timedelta(0) or lifetime > _MAX_LIFETIME:
        raise SecurityRecordError("Credential lifetime must be positive and no longer than 90 days.")

    issuer_metadata: dict[str, tuple[NodeIdentityStore, str]] = {}
    for store in issuers:
        metadata = store.load()
        node_id = metadata["node_id"]
        public_hex = metadata["public_key"]
        if node_id != _node_id(bytes.fromhex(public_hex)):
            raise SecurityRecordError("Issuer node identity does not match its public key.")
        if node_id in issuer_metadata:
            raise SecurityRecordError("Issuer quorum must contain distinct node identities.")
        issuer_metadata[node_id] = (store, public_hex)

    issued_at = instant.astimezone(timezone.utc)
    expires_at = issued_at + lifetime
    payload: dict[str, Any] = {
        "schema_version": 1,
        "record_type": "NODE_CORE_OS_SHIELD_IDENTITY_CREDENTIAL",
        "credential_id": "sha256:" + hashlib.sha256(
            _canonical({
                "subject_public_key": subject_public_key_hex,
                "subject_type": subject_type,
                "scopes": normalized_scopes,
                "issued_at": issued_at.isoformat(),
                "expires_at": expires_at.isoformat(),
            })
        ).hexdigest(),
        "subject_id": _node_id(raw_subject),
        "subject_public_key": subject_public_key_hex,
        "subject_type": subject_type,
        "scopes": normalized_scopes,
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "minimum_issuers": minimum_issuers,
    }
    message = _canonical(payload)
    signatures = []
    for issuer_id, (store, public_hex) in sorted(issuer_metadata.items()):
        signatures.append({
            "issuer_node_id": issuer_id,
            "issuer_public_key": public_hex,
            "signature": base64.b64encode(store.sign(message)).decode("ascii"),
        })
    payload["issuer_signatures"] = signatures
    return payload


def verify_quorum_identity_credential(
    credential: dict[str, Any],
    trusted_issuer_keys: dict[str, str],
    *,
    minimum_required_issuers: int = 3,
    required_scope: str | None = None,
    expected_subject_id: str | None = None,
    now: datetime | None = None,
) -> bool:
    """Verify a credential using receiver-owned issuer trust and authorization policy."""
    try:
        if not isinstance(credential, dict):
            return False
        if credential.get("schema_version") != 1:
            return False
        if credential.get("record_type") != "NODE_CORE_OS_SHIELD_IDENTITY_CREDENTIAL":
            return False

        subject_public_hex = credential["subject_public_key"]
        subject_raw = bytes.fromhex(subject_public_hex)
        Ed25519PublicKey.from_public_bytes(subject_raw)
        if len(subject_raw) != 32 or _node_id(subject_raw) != credential["subject_id"]:
            return False
        if expected_subject_id is not None and credential["subject_id"] != expected_subject_id:
            return False
        if credential.get("subject_type") not in _ALLOWED_SUBJECT_TYPES:
            return False
        scopes = credential["scopes"]
        if not isinstance(scopes, list) or not scopes or any(
            not isinstance(scope, str) or not scope or len(scope) > 128 for scope in scopes
        ):
            return False
        if len(set(scopes)) != len(scopes):
            return False
        if required_scope is not None and required_scope not in scopes:
            return False

        instant = now or datetime.now(timezone.utc)
        if instant.tzinfo is None:
            return False
        current = instant.astimezone(timezone.utc)
        issued_at = datetime.fromisoformat(credential["issued_at"].replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(credential["expires_at"].replace("Z", "+00:00"))
        if issued_at.tzinfo is None or expires_at.tzinfo is None:
            return False
        issued_at = issued_at.astimezone(timezone.utc)
        expires_at = expires_at.astimezone(timezone.utc)
        if issued_at > current or expires_at <= current or expires_at <= issued_at:
            return False
        if expires_at - issued_at > _MAX_LIFETIME:
            return False

        minimum_issuers = credential["minimum_issuers"]
        if (
            not isinstance(minimum_issuers, int)
            or isinstance(minimum_issuers, bool)
            or minimum_issuers < minimum_required_issuers
            or minimum_required_issuers < 2
        ):
            return False

        signatures = credential["issuer_signatures"]
        if not isinstance(signatures, list):
            return False
        payload = {key: value for key, value in credential.items() if key != "issuer_signatures"}
        message = _canonical(payload)
        valid_issuers = set()
        for item in signatures:
            if not isinstance(item, dict):
                continue
            issuer_id = item.get("issuer_node_id")
            public_hex = item.get("issuer_public_key")
            if not isinstance(issuer_id, str) or not isinstance(public_hex, str):
                continue
            if trusted_issuer_keys.get(issuer_id) != public_hex or issuer_id in valid_issuers:
                continue
            try:
                public_bytes = bytes.fromhex(public_hex)
                if len(public_bytes) != 32 or _node_id(public_bytes) != issuer_id:
                    continue
                signature = base64.b64decode(item["signature"], validate=True)
                Ed25519PublicKey.from_public_bytes(public_bytes).verify(signature, message)
            except (KeyError, TypeError, ValueError, InvalidSignature):
                continue
            valid_issuers.add(issuer_id)
        return len(valid_issuers) >= minimum_required_issuers
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
