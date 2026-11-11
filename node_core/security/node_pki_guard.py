"""NODE-PKI-GUARD local cryptographic primitives and fail-closed policy engine.

This module does not implement a blockchain, UTXO consensus, X.509 trust-store
validation, or external side-effect execution. Callers must validate the X.509
chain/hostname/revocation independently and provide an authoritative UTXO backend.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa

BINDING_FORMAT = "NODE-PKI-BINDING"
AUTH_FORMAT = "NODE-PKI-AUTH-UTXO"
PROTOCOL_VERSION = "1.0"
POP_DOMAIN = "NODE-PKI-GUARD-DUAL-POP"
IDEMPOTENCY_DOMAIN = "NODE-PKI-GUARD-IDEMPOTENCY-v1"
HEX_32 = re.compile(r"^[0-9a-f]{64}$")
B64URL = re.compile(r"^[A-Za-z0-9_-]+$")


class NodePKIGuardError(ValueError):
    """Invalid NODE-PKI-GUARD input or verification."""


class ReplayError(NodePKIGuardError):
    """A proof challenge has already been accepted."""


class PolicyError(NodePKIGuardError):
    """A binding or operation violates local policy."""


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64u(value: str) -> bytes:
    if not isinstance(value, str) or not B64URL.fullmatch(value):
        raise NodePKIGuardError("Invalid base64url signature")
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except Exception as exc:
        raise NodePKIGuardError("Invalid base64url signature") from exc


def canonical_json(value: Mapping[str, Any]) -> bytes:
    """Encode a restricted deterministic JSON profile for signed challenges.

    This profile rejects floats, non-ASCII object keys, unsafe integers and
    unsupported values. It is not a general-purpose RFC 8785 implementation.
    """
    def validate(item: Any, depth: int = 0) -> None:
        if depth > 32:
            raise NodePKIGuardError("Canonical JSON nesting limit exceeded")
        if item is None or isinstance(item, (str, bool)):
            return
        if type(item) is int:
            if abs(item) > 9007199254740991:
                raise NodePKIGuardError("Canonical JSON integer exceeds safe range")
            return
        if isinstance(item, float):
            raise NodePKIGuardError("Floating-point values are not permitted")
        if isinstance(item, list):
            if len(item) > 4096:
                raise NodePKIGuardError("Canonical JSON array is too large")
            for child in item:
                validate(child, depth + 1)
            return
        if isinstance(item, dict):
            if len(item) > 256:
                raise NodePKIGuardError("Canonical JSON object is too large")
            for key, child in item.items():
                if not isinstance(key, str) or not key.isascii():
                    raise NodePKIGuardError("Canonical JSON keys must be ASCII strings")
                validate(child, depth + 1)
            return
        raise NodePKIGuardError("Unsupported canonical JSON value")

    if not isinstance(value, Mapping):
        raise NodePKIGuardError("Canonical JSON root must be an object")
    validate(dict(value))
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def public_key_spki_sha256(public_key: Any) -> str:
    encoded = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return sha256_hex(encoded)


def certificate_fingerprints(certificate_pem_or_der: bytes) -> tuple[str, str]:
    """Return certificate SHA-256 and SPKI SHA-256 from PEM or DER X.509."""
    try:
        if b"-----BEGIN CERTIFICATE-----" in certificate_pem_or_der:
            cert = x509.load_pem_x509_certificate(certificate_pem_or_der)
        else:
            cert = x509.load_der_x509_certificate(certificate_pem_or_der)
    except ValueError as exc:
        raise NodePKIGuardError("Invalid X.509 certificate encoding") from exc
    return cert.fingerprint(hashes.SHA256()).hex(), public_key_spki_sha256(cert.public_key())


def _verify_signature(public_key: Any, message: bytes, signature: bytes) -> None:
    try:
        if isinstance(public_key, ed25519.Ed25519PublicKey):
            public_key.verify(signature, message)
        elif isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(signature, message, padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=hashes.SHA256().digest_size), hashes.SHA256())
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
        else:
            raise NodePKIGuardError("Unsupported proof-of-possession key type")
    except InvalidSignature as exc:
        raise NodePKIGuardError("Proof-of-possession signature is invalid") from exc


def sign_challenge(private_key: Any, challenge: Mapping[str, Any]) -> str:
    """Sign challenge bytes with Ed25519, RSA-PSS-SHA256 or ECDSA-SHA256."""
    message = canonical_json(challenge)
    if isinstance(private_key, ed25519.Ed25519PrivateKey):
        signature = private_key.sign(message)
    elif isinstance(private_key, rsa.RSAPrivateKey):
        signature = private_key.sign(message, padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=hashes.SHA256().digest_size), hashes.SHA256())
    elif isinstance(private_key, ec.EllipticCurvePrivateKey):
        signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
    else:
        raise NodePKIGuardError("Unsupported proof-of-possession private key type")
    return _b64u(signature)


class ChallengeRegistry:
    """Thread-safe local replay guard; distributed replay protection needs consensus."""
    def __init__(self) -> None:
        self._used: set[str] = set()
        self._lock = threading.Lock()

    def consume(self, challenge_id: str) -> None:
        if not isinstance(challenge_id, str) or not challenge_id:
            raise NodePKIGuardError("challenge_id is required")
        with self._lock:
            if challenge_id in self._used:
                raise ReplayError("Challenge has already been used")
            self._used.add(challenge_id)


def verify_dual_proof(*, challenge: Mapping[str, Any], node_public_key: Any,
                      x509_public_key: Any, node_signature: str,
                      x509_signature: str, registry: ChallengeRegistry,
                      now_epoch: int | None = None) -> str:
    """Verify both keys over one context-bound challenge and consume its local ID.

    X.509 chain, hostname, EKU, validity and revocation checks are caller duties.
    The X.509 public key must come from that independently validated certificate.
    """
    required = {"domain", "version", "challenge_id", "nonce", "node_id",
                "x509_fingerprint_sha256", "spki_sha256", "purpose", "audience",
                "operation_hash", "issued_at", "expires_at"}
    if set(challenge) != required:
        raise NodePKIGuardError("Challenge fields do not match the required profile")
    if challenge["domain"] != POP_DOMAIN or challenge["version"] != PROTOCOL_VERSION:
        raise NodePKIGuardError("Unsupported proof challenge domain or version")
    if not isinstance(challenge["nonce"], str) or len(_unb64u(challenge["nonce"])) < 32:
        raise NodePKIGuardError("Challenge nonce must contain at least 256 random bits")
    for field in ("x509_fingerprint_sha256", "spki_sha256", "operation_hash"):
        if not isinstance(challenge[field], str) or not HEX_32.fullmatch(challenge[field]):
            raise NodePKIGuardError("Invalid " + field)
    for field in ("node_id", "purpose", "audience", "challenge_id"):
        if not isinstance(challenge[field], str) or not challenge[field]:
            raise NodePKIGuardError(field + " is required")
    if type(challenge["issued_at"]) is not int or type(challenge["expires_at"]) is not int:
        raise NodePKIGuardError("Challenge timestamps must be integer epoch seconds")
    now = int(time.time()) if now_epoch is None else now_epoch
    if challenge["expires_at"] <= challenge["issued_at"] or challenge["expires_at"] - challenge["issued_at"] > 600:
        raise NodePKIGuardError("Challenge lifetime must be between 1 and 600 seconds")
    if challenge["issued_at"] > now + 30 or challenge["expires_at"] <= now:
        raise NodePKIGuardError("Challenge is not currently valid")
    message = canonical_json(challenge)
    _verify_signature(node_public_key, message, _unb64u(node_signature))
    _verify_signature(x509_public_key, message, _unb64u(x509_signature))
    registry.consume(challenge["challenge_id"])
    return sha256_hex(message)


def validate_binding(binding: Mapping[str, Any]) -> None:
    required = {"format", "version", "binding_id", "node_id",
                "x509_fingerprint_sha256", "spki_sha256", "purpose",
                "allowed_operations", "denied_operations", "constraints",
                "issuer_key_id", "issued_at", "expires_at", "binding_status",
                "proof_of_possession", "issuer_signature"}
    if set(binding) != required:
        raise NodePKIGuardError("Binding fields do not match the NODE-PKI-BINDING profile")
    if binding["format"] != BINDING_FORMAT or binding["version"] != PROTOCOL_VERSION:
        raise NodePKIGuardError("Unsupported binding format or version")
    for field in ("binding_id", "node_id", "purpose", "issuer_key_id"):
        if not isinstance(binding[field], str) or not binding[field]:
            raise NodePKIGuardError(field + " is required")
    for field in ("x509_fingerprint_sha256", "spki_sha256"):
        if not isinstance(binding[field], str) or not HEX_32.fullmatch(binding[field]):
            raise NodePKIGuardError("Invalid " + field)
    if binding["binding_status"] not in {"ACTIVE", "SUSPENDED", "REVOKED", "EXPIRED"}:
        raise NodePKIGuardError("Invalid binding_status")
    for field in ("allowed_operations", "denied_operations"):
        if not isinstance(binding[field], list) or not all(isinstance(x, str) for x in binding[field]):
            raise NodePKIGuardError(field + " must be an array of strings")
    if not isinstance(binding["constraints"], dict) or not isinstance(binding["proof_of_possession"], dict):
        raise NodePKIGuardError("constraints and proof_of_possession must be objects")
    if not isinstance(binding["issuer_signature"], str) or not binding["issuer_signature"]:
        raise NodePKIGuardError("issuer_signature is required")
    if type(binding["issued_at"]) is not int or type(binding["expires_at"]) is not int:
        raise NodePKIGuardError("Binding timestamps must be integer epoch seconds")
    if binding["expires_at"] <= binding["issued_at"]:
        raise NodePKIGuardError("Binding expiry must follow issue time")


def validate_authorization(auth: Mapping[str, Any]) -> None:
    required = {"format", "version", "authorization_id", "outpoint", "binding_id",
                "node_id", "operation", "operation_hash", "audience", "policy_id",
                "policy_version", "context_hash", "valid_from_epoch",
                "valid_until_epoch", "required_signatures", "single_use"}
    if set(auth) != required:
        raise NodePKIGuardError("Authorization fields do not match the NODE-PKI-AUTH-UTXO profile")
    if auth["format"] != AUTH_FORMAT or auth["version"] != PROTOCOL_VERSION:
        raise NodePKIGuardError("Unsupported authorization format or version")
    for field in ("authorization_id", "outpoint", "binding_id", "node_id",
                  "operation", "audience", "policy_id", "policy_version"):
        if not isinstance(auth[field], str) or not auth[field]:
            raise NodePKIGuardError(field + " is required")
    if not re.fullmatch(r"[0-9a-f]{64}:[0-9]{1,10}", auth["outpoint"]):
        raise NodePKIGuardError("outpoint must use lowercase txid:vout notation")
    for field in ("operation_hash", "context_hash"):
        if not isinstance(auth[field], str) or not HEX_32.fullmatch(auth[field]):
            raise NodePKIGuardError("Invalid " + field)
    if type(auth["valid_from_epoch"]) is not int or type(auth["valid_until_epoch"]) is not int:
        raise NodePKIGuardError("Authorization epochs must be integers")
    if auth["valid_until_epoch"] <= auth["valid_from_epoch"]:
        raise NodePKIGuardError("Authorization validity window is empty")
    if auth["single_use"] is not True:
        raise NodePKIGuardError("NODE-PKI-AUTH-UTXO must be single-use")
    if not isinstance(auth["required_signatures"], list) or not auth["required_signatures"]:
        raise NodePKIGuardError("required_signatures must be a non-empty array")


def verify_binding_signature(binding: Mapping[str, Any],
                              trusted_issuer_keys: Mapping[str, Any]) -> None:
    """Verify issuer signature over all binding fields except issuer_signature."""
    key_id = binding.get("issuer_key_id")
    if not isinstance(key_id, str) or key_id not in trusted_issuer_keys:
        raise NodePKIGuardError("Binding issuer key is not trusted")
    unsigned = {key: value for key, value in binding.items() if key != "issuer_signature"}
    _verify_signature(trusted_issuer_keys[key_id], canonical_json(unsigned),
                      _unb64u(binding["issuer_signature"]))


class UTXOView(Protocol):
    def get_unspent_authorization(self, outpoint: str) -> Mapping[str, Any] | None:
        """Return an unspent authorization from an authoritative state view."""


@dataclass(frozen=True)
class AuthorizationDecision:
    decision: str
    reason: str
    operation_hash: str
    authorization_id: str | None = None
    outpoint: str | None = None


def operation_digest(operation_context: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json({
        "domain": IDEMPOTENCY_DOMAIN, "context": dict(operation_context)
    }))


def evaluate_authorization(*, mode: str, operation_context: Mapping[str, Any],
                           binding: Mapping[str, Any] | None,
                           authorization: Mapping[str, Any] | None,
                           utxo_view: UTXOView | None, trusted_binding_issuers: Mapping[str, Any] | None,
                           now_epoch: int, current_epoch: int, x509_validated: bool,
                           dual_proof_verified: bool) -> AuthorizationDecision:
    """Evaluate only; never spends a UTXO or executes an external operation."""
    try:
        op_hash = operation_digest(operation_context)
    except NodePKIGuardError as exc:
        return AuthorizationDecision("DENY", str(exc), "")
    if mode not in {"STANDARD", "PROTECTED", "DENY"}:
        return AuthorizationDecision("DENY", "Unknown policy mode", op_hash)
    if mode == "DENY":
        return AuthorizationDecision("DENY", "Operation denied by policy", op_hash)
    if mode == "STANDARD":
        if not x509_validated:
            return AuthorizationDecision("DENY", "X.509 validation is required", op_hash)
        return AuthorizationDecision("STANDARD", "Conventional X.509 path accepted; no UTXO is consumed", op_hash)
    try:
        if not x509_validated:
            raise PolicyError("X.509 validation is required")
        if not dual_proof_verified:
            raise PolicyError("Dual proof-of-possession is required")
        if binding is None or authorization is None or utxo_view is None or trusted_binding_issuers is None:
            raise PolicyError("Binding, trusted issuer keys, authorization and authoritative UTXO view are required")
        validate_binding(binding)
        verify_binding_signature(binding, trusted_binding_issuers)
        validate_authorization(authorization)
        if binding["binding_status"] != "ACTIVE":
            raise PolicyError("Binding is not active")
        if not binding["issued_at"] <= now_epoch < binding["expires_at"]:
            raise PolicyError("Binding is outside its validity window")
        if binding["node_id"] != operation_context.get("node_id"):
            raise PolicyError("Operation node identity does not match binding")
        operation, audience = operation_context.get("operation"), operation_context.get("audience")
        if operation in binding["denied_operations"] or operation not in binding["allowed_operations"]:
            raise PolicyError("Operation is not allowed by binding")
        if authorization["binding_id"] != binding["binding_id"] or authorization["node_id"] != binding["node_id"]:
            raise PolicyError("Authorization is not bound to this identity")
        if authorization["operation"] != operation or authorization["audience"] != audience:
            raise PolicyError("Authorization operation or audience mismatch")
        if authorization["operation_hash"] != op_hash:
            raise PolicyError("Authorization operation hash mismatch")
        if not authorization["valid_from_epoch"] <= current_epoch < authorization["valid_until_epoch"]:
            raise PolicyError("Authorization is outside its consensus epoch window")
        record = utxo_view.get_unspent_authorization(authorization["outpoint"])
        if record is None:
            raise PolicyError("Authorization UTXO is missing or already spent")
        if dict(record) != dict(authorization):
            raise PolicyError("Ledger authorization data does not match supplied authorization")
        return AuthorizationDecision(
            "PROTECTED",
            "Preconditions passed; submit UTXO spend and wait for consensus finality before execution",
            op_hash, authorization["authorization_id"], authorization["outpoint"])
    except (NodePKIGuardError, KeyError, TypeError) as exc:
        return AuthorizationDecision("DENY", str(exc), op_hash)
