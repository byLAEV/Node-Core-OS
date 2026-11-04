"""Mutual cryptographic authentication helpers for Node Core OS P2P peers.

This module builds and verifies bounded handshake messages. It does not open
sockets, encrypt traffic, discover peers, or manage connection lifecycle.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from node_core.identity.node_identity import NodeIdentityError, NodeIdentityStore


class PeerAuthenticationError(RuntimeError):
    """Raised when a peer handshake message is invalid or unauthenticated."""


class PeerAuthenticator:
    """Create and verify a nonce-bound, mutually authenticated peer handshake."""

    PROTOCOL_VERSION = 1
    PURPOSE = "node-core-os/p2p-peer-authentication/v1"
    ROLES = frozenset({"initiator", "responder"})
    NONCE_BYTES = 32
    PUBLIC_KEY_BYTES = 32
    SIGNATURE_BYTES = 64
    MAX_HANDSHAKE_MESSAGE_BYTES = 4096
    _HEX = frozenset("0123456789abcdef")

    @classmethod
    def _is_lower_hex(cls, value: object, length: int) -> bool:
        return (
            isinstance(value, str)
            and len(value) == length
            and all(character in cls._HEX for character in value)
        )

    @classmethod
    def _canonical(cls, payload: dict[str, Any]) -> bytes:
        try:
            encoded = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("ascii")
        except (TypeError, ValueError) as exc:
            raise PeerAuthenticationError("Handshake transcript is not canonical JSON.") from exc
        if not encoded or len(encoded) > cls.MAX_HANDSHAKE_MESSAGE_BYTES:
            raise PeerAuthenticationError("Handshake transcript exceeds the size limit.")
        return encoded

    @classmethod
    def create_hello(cls, identity_store: NodeIdentityStore) -> dict[str, Any]:
        """Create a public hello with a fresh 256-bit nonce."""
        try:
            metadata = identity_store.load()
        except NodeIdentityError as exc:
            raise PeerAuthenticationError("Local technical identity is unavailable.") from exc
        hello = {
            "type": "HELLO",
            "protocol_version": cls.PROTOCOL_VERSION,
            "node_id": metadata["node_id"],
            "public_key": metadata["public_key"],
            "nonce": secrets.token_hex(cls.NONCE_BYTES),
        }
        cls._validate_hello(hello)
        return hello

    @classmethod
    def create_auth(
        cls,
        identity_store: NodeIdentityStore,
        local_hello: dict[str, Any],
        remote_hello: dict[str, Any],
        local_role: str,
    ) -> dict[str, Any]:
        """Sign the complete two-hello transcript to prove local key control."""
        cls._validate_role(local_role)
        cls._validate_hello(local_hello)
        cls._validate_hello(remote_hello)
        cls._ensure_distinct_peers(local_hello, remote_hello)
        try:
            metadata = identity_store.load()
            if (
                metadata["node_id"] != local_hello["node_id"]
                or metadata["public_key"] != local_hello["public_key"]
            ):
                raise PeerAuthenticationError("Local HELLO does not match the local identity.")
            transcript = cls._transcript(local_hello, remote_hello, local_role)
            signature = identity_store.sign(transcript)
        except NodeIdentityError as exc:
            raise PeerAuthenticationError("Unable to sign peer authentication transcript.") from exc
        if not isinstance(signature, bytes) or len(signature) != cls.SIGNATURE_BYTES:
            raise PeerAuthenticationError("Local identity returned an invalid signature.")
        auth = {
            "type": "AUTH",
            "protocol_version": cls.PROTOCOL_VERSION,
            "node_id": metadata["node_id"],
            "public_key": metadata["public_key"],
            "transcript_sha256": hashlib.sha256(transcript).hexdigest(),
            "signature": signature.hex(),
        }
        cls._validate_auth_shape(auth)
        return auth

    @classmethod
    def verify_auth(
        cls,
        auth_message: dict[str, Any],
        expected_peer_hello: dict[str, Any],
        local_hello: dict[str, Any],
        local_role: str,
    ) -> dict[str, str]:
        """Verify the peer's signature and return the authenticated public identity."""
        cls._validate_role(local_role)
        cls._validate_hello(expected_peer_hello)
        cls._validate_hello(local_hello)
        cls._ensure_distinct_peers(local_hello, expected_peer_hello)
        cls._validate_auth_shape(auth_message)
        if (
            auth_message["node_id"] != expected_peer_hello["node_id"]
            or auth_message["public_key"] != expected_peer_hello["public_key"]
        ):
            raise PeerAuthenticationError("AUTH identity does not match the peer HELLO.")
        transcript = cls._transcript(local_hello, expected_peer_hello, local_role)
        expected_hash = hashlib.sha256(transcript).hexdigest()
        if auth_message["transcript_sha256"] != expected_hash:
            raise PeerAuthenticationError("AUTH transcript does not match this handshake.")
        try:
            signature = bytes.fromhex(auth_message["signature"])
            public_bytes = bytes.fromhex(expected_peer_hello["public_key"])
            public_key = Ed25519PublicKey.from_public_bytes(public_bytes)
            public_key.verify(signature, transcript)
        except (ValueError, TypeError, KeyError, InvalidSignature) as exc:
            raise PeerAuthenticationError("Peer signature is invalid.") from exc
        return {
            "node_id": expected_peer_hello["node_id"],
            "public_key": expected_peer_hello["public_key"],
            "authentication": "ed25519_mutual_challenge_response",
        }

    @classmethod
    def _validate_hello(cls, hello: dict[str, Any]) -> None:
        if not isinstance(hello, dict) or set(hello) != {
            "type", "protocol_version", "node_id", "public_key", "nonce"
        }:
            raise PeerAuthenticationError("HELLO fields are invalid.")
        if (
            hello["type"] != "HELLO"
            or type(hello["protocol_version"]) is not int
            or hello["protocol_version"] != cls.PROTOCOL_VERSION
        ):
            raise PeerAuthenticationError("Unsupported or malformed HELLO message.")
        node_id = hello["node_id"]
        public_key_hex = hello["public_key"]
        nonce = hello["nonce"]
        if (
            not isinstance(node_id, str)
            or len(node_id) != 71
            or not node_id.startswith("sha256:")
            or any(character not in cls._HEX for character in node_id[7:])
        ):
            raise PeerAuthenticationError("HELLO node ID is invalid.")
        if not cls._is_lower_hex(public_key_hex, cls.PUBLIC_KEY_BYTES * 2):
            raise PeerAuthenticationError("HELLO public key is invalid.")
        if not cls._is_lower_hex(nonce, cls.NONCE_BYTES * 2):
            raise PeerAuthenticationError("HELLO nonce is invalid.")
        public_bytes = bytes.fromhex(public_key_hex)
        expected_id = "sha256:" + hashlib.sha256(public_bytes).hexdigest()
        if node_id != expected_id:
            raise PeerAuthenticationError("HELLO node ID does not match its public key.")
        cls._canonical(hello)

    @classmethod
    def _validate_auth_shape(cls, auth_message: dict[str, Any]) -> None:
        if not isinstance(auth_message, dict) or set(auth_message) != {
            "type", "protocol_version", "node_id", "public_key",
            "transcript_sha256", "signature"
        }:
            raise PeerAuthenticationError("AUTH fields are invalid.")
        if (
            auth_message["type"] != "AUTH"
            or type(auth_message["protocol_version"]) is not int
            or auth_message["protocol_version"] != cls.PROTOCOL_VERSION
        ):
            raise PeerAuthenticationError("Unsupported or malformed AUTH message.")
        node_id = auth_message["node_id"]
        if (
            not isinstance(node_id, str)
            or len(node_id) != 71
            or not node_id.startswith("sha256:")
            or any(character not in cls._HEX for character in node_id[7:])
        ):
            raise PeerAuthenticationError("AUTH node ID is invalid.")
        if not cls._is_lower_hex(auth_message["public_key"], cls.PUBLIC_KEY_BYTES * 2):
            raise PeerAuthenticationError("AUTH public key is invalid.")
        if not cls._is_lower_hex(auth_message["transcript_sha256"], 64):
            raise PeerAuthenticationError("AUTH transcript digest is invalid.")
        if not cls._is_lower_hex(auth_message["signature"], cls.SIGNATURE_BYTES * 2):
            raise PeerAuthenticationError("AUTH signature is invalid.")
        cls._canonical(auth_message)

    @classmethod
    def _ensure_distinct_peers(
        cls, first: dict[str, Any], second: dict[str, Any]
    ) -> None:
        if first["node_id"] == second["node_id"]:
            raise PeerAuthenticationError("A node cannot authenticate a connection to itself.")

    @classmethod
    def _transcript(
        cls,
        local_hello: dict[str, Any],
        remote_hello: dict[str, Any],
        local_role: str,
    ) -> bytes:
        if local_role == "initiator":
            initiator, responder = local_hello, remote_hello
        else:
            initiator, responder = remote_hello, local_hello
        payload = {
            "purpose": cls.PURPOSE,
            "protocol_version": cls.PROTOCOL_VERSION,
            "initiator": initiator,
            "responder": responder,
        }
        return cls._canonical(payload)

    @classmethod
    def _validate_role(cls, role: str) -> None:
        if role not in cls.ROLES:
            raise PeerAuthenticationError("Role must be 'initiator' or 'responder'.")
