"""One-shot LAN identity proof messages, separate from peer trust and sessions.

This module proves control of an Ed25519 node identity for a fresh challenge.
It does not encrypt traffic, establish a session, authorize a peer, or add trust.
Callers must generate and retain a fresh challenge nonce for each attempt.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any

from node_core.identity.node_identity import NodeIdentityError, NodeIdentityStore


PROTOCOL_VERSION = 1
PURPOSE = "node-core-os/p2p-lan-identity-proof/v1"
NONCE_BYTES = 32
MAX_MESSAGE_BYTES = 4096


class IdentityProofError(ValueError):
    """Raised when a one-shot LAN identity proof is malformed or invalid."""


def _canonical(value: dict[str, Any]) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise IdentityProofError("Identity proof message is not canonical JSON.") from exc


def create_challenge() -> dict[str, Any]:
    """Create an unpredictable 256-bit challenge for one identity-proof attempt."""
    return {
        "type": "IDENTITY_CHALLENGE",
        "protocol_version": PROTOCOL_VERSION,
        "purpose": PURPOSE,
        "nonce": secrets.token_hex(NONCE_BYTES),
    }


def _validate_challenge(challenge: dict[str, Any]) -> bytes:
    if not isinstance(challenge, dict) or set(challenge) != {
        "type", "protocol_version", "purpose", "nonce"
    }:
        raise IdentityProofError("Identity challenge fields are invalid.")
    if (
        challenge["type"] != "IDENTITY_CHALLENGE"
        or type(challenge["protocol_version"]) is not int
        or challenge["protocol_version"] != PROTOCOL_VERSION
        or challenge["purpose"] != PURPOSE
    ):
        raise IdentityProofError("Unsupported identity challenge.")
    nonce = challenge["nonce"]
    if not isinstance(nonce, str):
        raise IdentityProofError("Identity challenge nonce is invalid.")
    try:
        raw_nonce = bytes.fromhex(nonce)
    except ValueError as exc:
        raise IdentityProofError("Identity challenge nonce is not hexadecimal.") from exc
    if len(raw_nonce) != NONCE_BYTES:
        raise IdentityProofError("Identity challenge nonce must be 32 bytes.")
    return raw_nonce


def create_response(
    identity_store: NodeIdentityStore, challenge: dict[str, Any]
) -> dict[str, Any]:
    """Sign a fresh challenge with the persistent Ed25519 node identity."""
    _validate_challenge(challenge)
    try:
        identity = identity_store.load()
        signed_fields = {
            "purpose": PURPOSE,
            "protocol_version": PROTOCOL_VERSION,
            "challenge": challenge,
            "node_id": identity["node_id"],
            "public_key": identity["public_key"],
        }
        signature = identity_store.sign(_canonical(signed_fields))
    except NodeIdentityError as exc:
        raise IdentityProofError("Local node identity is unavailable.") from exc
    response = {
        "type": "IDENTITY_PROOF",
        "protocol_version": PROTOCOL_VERSION,
        "node_id": identity["node_id"],
        "public_key": identity["public_key"],
        "signature": signature.hex(),
    }
    if len(_canonical(response)) > MAX_MESSAGE_BYTES:
        raise IdentityProofError("Identity proof exceeds the size limit.")
    return response


def verify_response(
    challenge: dict[str, Any], response: dict[str, Any]
) -> dict[str, str]:
    """Verify proof of key possession and return public identity; never grant trust."""
    _validate_challenge(challenge)
    if not isinstance(response, dict) or set(response) != {
        "type", "protocol_version", "node_id", "public_key", "signature"
    }:
        raise IdentityProofError("Identity proof fields are invalid.")
    if (
        response["type"] != "IDENTITY_PROOF"
        or type(response["protocol_version"]) is not int
        or response["protocol_version"] != PROTOCOL_VERSION
    ):
        raise IdentityProofError("Unsupported identity proof.")
    node_id = response["node_id"]
    public_key = response["public_key"]
    signature_text = response["signature"]
    if not isinstance(public_key, str) or len(public_key) != 64:
        raise IdentityProofError("Identity proof public key is invalid.")
    try:
        public_bytes = bytes.fromhex(public_key)
        signature = bytes.fromhex(signature_text)
    except (TypeError, ValueError) as exc:
        raise IdentityProofError("Identity proof key or signature is malformed.") from exc
    if len(public_bytes) != 32 or len(signature) != 64:
        raise IdentityProofError("Identity proof key or signature has an invalid length.")
    expected_node_id = "sha256:" + hashlib.sha256(public_bytes).hexdigest()
    if node_id != expected_node_id:
        raise IdentityProofError("Identity proof node ID does not match its public key.")
    signed_fields = {
        "purpose": PURPOSE,
        "protocol_version": PROTOCOL_VERSION,
        "challenge": challenge,
        "node_id": node_id,
        "public_key": public_key,
    }
    if not NodeIdentityStore.verify(public_key, _canonical(signed_fields), signature):
        raise IdentityProofError("Identity proof signature is invalid.")
    return {
        "node_id": node_id,
        "public_key": public_key,
        "authentication": "ed25519_fresh_challenge_response",
        "trust_status": "not_trusted",
        "authorization": "none",
        "session_established": "false",
    }
