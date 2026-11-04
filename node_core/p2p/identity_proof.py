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
PUBLIC_KEY_BYTES = 32
SIGNATURE_BYTES = 64
MAX_MESSAGE_BYTES = 4096
_HEX = frozenset("0123456789abcdef")


class IdentityProofError(ValueError):
    """Raised when a one-shot LAN identity proof is malformed or invalid."""


def _canonical(value: dict[str, Any]) -> bytes:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise IdentityProofError("Identity proof message is not canonical JSON.") from exc
    if not encoded or len(encoded) > MAX_MESSAGE_BYTES:
        raise IdentityProofError("Identity proof message exceeds the size limit.")
    return encoded


def _is_lower_hex(value: object, expected_length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == expected_length
        and all(character in _HEX for character in value)
    )


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
    if not _is_lower_hex(nonce, NONCE_BYTES * 2):
        raise IdentityProofError("Identity challenge nonce must be 32-byte lowercase hexadecimal.")
    return bytes.fromhex(nonce)


def create_response(
    identity_store: NodeIdentityStore, challenge: dict[str, Any]
) -> dict[str, Any]:
    """Sign a fresh challenge with the persistent Ed25519 node identity."""
    _validate_challenge(challenge)
    try:
        identity = identity_store.load()
        public_key = identity["public_key"]
        node_id = identity["node_id"]
        if not _is_lower_hex(public_key, PUBLIC_KEY_BYTES * 2):
            raise IdentityProofError("Local node public key metadata is invalid.")
        if node_id != "sha256:" + hashlib.sha256(bytes.fromhex(public_key)).hexdigest():
            raise IdentityProofError("Local node ID does not match its public key.")
        signed_fields = {
            "purpose": PURPOSE,
            "protocol_version": PROTOCOL_VERSION,
            "challenge": challenge,
            "node_id": node_id,
            "public_key": public_key,
        }
        signature = identity_store.sign(_canonical(signed_fields))
    except NodeIdentityError as exc:
        raise IdentityProofError("Local node identity is unavailable.") from exc
    if not isinstance(signature, bytes) or len(signature) != SIGNATURE_BYTES:
        raise IdentityProofError("Local identity returned an invalid signature.")
    response = {
        "type": "IDENTITY_PROOF",
        "protocol_version": PROTOCOL_VERSION,
        "node_id": node_id,
        "public_key": public_key,
        "signature": signature.hex(),
    }
    _canonical(response)
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
    if (
        not isinstance(node_id, str)
        or len(node_id) != 71
        or not node_id.startswith("sha256:")
        or any(character not in _HEX for character in node_id[7:])
    ):
        raise IdentityProofError("Identity proof node ID is invalid.")
    if not _is_lower_hex(public_key, PUBLIC_KEY_BYTES * 2):
        raise IdentityProofError("Identity proof public key is invalid.")
    if not _is_lower_hex(signature_text, SIGNATURE_BYTES * 2):
        raise IdentityProofError("Identity proof signature is invalid.")
    _canonical(response)
    public_bytes = bytes.fromhex(public_key)
    signature = bytes.fromhex(signature_text)
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
