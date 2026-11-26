"""Signed, interoperable Node Core OS node identity certificates.

Format: compact JWS using EdDSA (Ed25519), with an explicit Node Core OS
certificate media type. This is a project-defined credential profile, not an
X.509 certificate or a claim of third-party/international accreditation.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json
import re
import uuid
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

FORMAT = "node-core-os-node-identity"
FORMAT_VERSION = "1.0"
JWS_TYPE = "NODECORE-CERT+JWT"
ALGORITHM = "EdDSA"
MAX_LIFETIME = timedelta(days=90)
HEX_32 = re.compile(r"^[0-9a-fA-F]{64}$")
PROFILES = frozenset({
    "sybil-resistance",
    "p2p-partition-eclipse-resistance",
    "byzantine-collusion-resistance",
    "identity-key-protection",
    "software-supply-chain-integrity",
    "availability-ddos-resistance",
    "ipfs-content-integrity",
    "privilege-and-pool-isolation",
})


class NodeCertificateError(ValueError):
    """Raised when a node certificate cannot be safely issued or verified."""


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64u(value: str) -> bytes:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]*", value):
        raise NodeCertificateError("Invalid base64url value")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _parse_json_segment(segment: str) -> dict[str, Any]:
    try:
        value = json.loads(_unb64u(segment).decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NodeCertificateError("Malformed JWS JSON segment") from exc
    if not isinstance(value, dict):
        raise NodeCertificateError("JWS JSON segment must be an object")
    return value


def issue_certificate(
    *,
    issuer_id: str,
    issuer_key_id: str,
    issuer_private_key: Ed25519PrivateKey,
    node_id: str,
    node_public_key_hex: str,
    profile: str,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    metadata: Mapping[str, str] | None = None,
) -> str:
    """Issue a compact signed certificate; private key never enters the token."""
    if not issuer_id.strip() or not issuer_key_id.strip() or not node_id.strip():
        raise NodeCertificateError("issuer_id, issuer_key_id and node_id are required")
    if not isinstance(node_public_key_hex, str) or not HEX_32.fullmatch(node_public_key_hex):
        raise NodeCertificateError("node_public_key_hex must be a 32-byte Ed25519 public key in hex")
    if profile not in PROFILES:
        raise NodeCertificateError("Unsupported certificate profile")
    now = issued_at or datetime.now(timezone.utc)
    expiry = expires_at or (now + timedelta(days=30))
    if now.tzinfo is None or expiry.tzinfo is None:
        raise NodeCertificateError("Timestamps must be timezone-aware")
    now = now.astimezone(timezone.utc)
    expiry = expiry.astimezone(timezone.utc)
    if expiry <= now:
        raise NodeCertificateError("Certificate expiry must be after issue time")
    if expiry - now > MAX_LIFETIME:
        raise NodeCertificateError("Certificate lifetime cannot exceed 90 days")
    if metadata is not None:
        if not isinstance(metadata, Mapping) or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in metadata.items()
        ):
            raise NodeCertificateError("metadata must be a string-to-string object")
        if len(metadata) > 32 or any(len(k) > 64 or len(v) > 256 for k, v in metadata.items()):
            raise NodeCertificateError("metadata exceeds size limits")

    header = {"alg": ALGORITHM, "kid": issuer_key_id, "typ": JWS_TYPE}
    claims: dict[str, Any] = {
        "iss": issuer_id,
        "sub": node_id,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expiry.timestamp()),
        "node_core": {
            "format": FORMAT,
            "version": FORMAT_VERSION,
            "profile": profile,
            "subject_public_key": node_public_key_hex.lower(),
        },
    }
    if metadata:
        claims["node_core"]["metadata"] = dict(metadata)
    signing_input = _b64u(_json_bytes(header)) + "." + _b64u(_json_bytes(claims))
    signature = issuer_private_key.sign(signing_input.encode("ascii"))
    return signing_input + "." + _b64u(signature)


def verify_certificate(
    token: str,
    *,
    trusted_issuers: Mapping[str, bytes | Ed25519PublicKey],
    trusted_issuer_ids: Mapping[str, str],
    now: datetime | None = None,
    revoked_ids: set[str] | frozenset[str] = frozenset(),
    clock_skew_seconds: int = 60,
) -> dict[str, Any]:
    """Verify signature, issuer trust, profile, time bounds, and local revocation.

    trusted_issuers maps the JOSE kid to an independently trusted issuer public key.
    trusted_issuer_ids must map the same kid to its expected issuer identity; this
    prevents a trusted signing key from asserting an arbitrary "iss" claim.
    The caller is responsible for distributing both trust mappings and fresh revocation data.
    """
    if not isinstance(token, str) or len(token) > 16384:
        raise NodeCertificateError("Certificate must be a compact token under 16 KiB")
    parts = token.split(".")
    if len(parts) != 3:
        raise NodeCertificateError("Certificate must contain three compact JWS segments")
    header = _parse_json_segment(parts[0])
    claims = _parse_json_segment(parts[1])
    if header != {"alg": ALGORITHM, "kid": header.get("kid"), "typ": JWS_TYPE}:
        raise NodeCertificateError("Unsupported or unsafe JWS header")
    kid = header.get("kid")
    if not isinstance(kid, str) or kid not in trusted_issuers:
        raise NodeCertificateError("Issuer key is not trusted")
    expected_issuer_id = trusted_issuer_ids.get(kid)
    if not isinstance(expected_issuer_id, str) or not expected_issuer_id.strip():
        raise NodeCertificateError("Trusted issuer identity is missing for issuer key")
    if claims.get("iss") != expected_issuer_id:
        raise NodeCertificateError("Issuer identity does not match the trusted issuer key")
    key_value = trusted_issuers[kid]
    try:
        public_key = key_value if isinstance(key_value, Ed25519PublicKey) else Ed25519PublicKey.from_public_bytes(key_value)
        public_key.verify(_unb64u(parts[2]), (parts[0] + "." + parts[1]).encode("ascii"))
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise NodeCertificateError("Certificate signature is invalid") from exc

    required = {"iss", "sub", "jti", "iat", "nbf", "exp", "node_core"}
    if not required.issubset(claims):
        raise NodeCertificateError("Certificate is missing required claims")
    core = claims["node_core"]
    if not isinstance(core, dict) or core.get("format") != FORMAT or core.get("version") != FORMAT_VERSION:
        raise NodeCertificateError("Unsupported Node Core certificate format")
    if core.get("profile") not in PROFILES:
        raise NodeCertificateError("Unsupported certificate profile")
    if not isinstance(core.get("subject_public_key"), str) or not HEX_32.fullmatch(core["subject_public_key"]):
        raise NodeCertificateError("Invalid subject public key")
    if not all(isinstance(claims.get(k), str) and claims[k] for k in ("iss", "sub", "jti")):
        raise NodeCertificateError("Issuer, subject and certificate ID must be non-empty strings")
    if any(type(claims.get(k)) is not int for k in ("iat", "nbf", "exp")):
        raise NodeCertificateError("iat, nbf and exp must be integer NumericDate values")
    if claims["exp"] <= claims["iat"] or claims["nbf"] < claims["iat"]:
        raise NodeCertificateError("Invalid certificate time ordering")
    if claims["exp"] - claims["iat"] > int(MAX_LIFETIME.total_seconds()):
        raise NodeCertificateError("Certificate lifetime exceeds 90 days")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise NodeCertificateError("Verification time must be timezone-aware")
    timestamp = current.timestamp()
    if claims["nbf"] > timestamp + clock_skew_seconds:
        raise NodeCertificateError("Certificate is not yet valid")
    if claims["iat"] > timestamp + clock_skew_seconds:
        raise NodeCertificateError("Certificate issue time is in the future")
    if claims["exp"] <= timestamp - clock_skew_seconds:
        raise NodeCertificateError("Certificate has expired")
    if claims["jti"] in revoked_ids:
        raise NodeCertificateError("Certificate is revoked")
    return claims
