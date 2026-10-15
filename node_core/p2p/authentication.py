"""Mutual cryptographic authentication helpers for Node Core OS P2P peers.

This module builds and verifies handshake messages. It does not open sockets,
encrypt traffic, discover peers, or manage connection lifecycle.
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
    ROLES = {"initiator", "responder"}

    @classmethod
    def create_hello(cls, identity_store: NodeIdentityStore) -> dict[str, Any]:
        """Create a public hello with a fresh 256-bit nonce."""
        try:
            metadata = identity_store.load()
        except NodeIdentityError as exc:
            raise PeerAuthenticationError("Local technical identity is unavailable.") from exc
        return {
            "type": "HELLO",
            "protocol_version": cls.PROTOCOL_VERSION,
            "node_id": metadata["node_id"],
            "public_key": metadata["public_key"],
            "nonce": secrets.token_hex(32),
        }

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
        metadata = identity_store.load()
        if (
            metadata["node_id"] != local_hello["node_id"]
            or metadata["public_key"] != local_hello["public_key"]
        ):
            raise PeerAuthenticationError("Local HELLO does not match the local identity.")
        transcript = cls._transcript(local_hello, remote_hello, local_role)
        try:
            signature = identity_store.sign(transcript)
        except NodeIdentityError as exc:
            raise PeerAuthenticationError("Unable to sign peer authentication transcript.") from exc
        return {
            "type": "AUTH",
            "protocol_version": cls.PROTOCOL_VERSION,
            "node_id": metadata["node_id"],
            "public_key": metadata["public_key"],
            "transcript_sha256": hashlib.sha256(transcript).hexdigest(),
            "signature": signature.hex(),
        }

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
        if not isinstance(auth_message, dict):
            raise PeerAuthenticationError("AUTH message must be an object.")
        if (
            auth_message.get("type") != "AUTH"
            or auth_message.get("protocol_version") != cls.PROTOCOL_VERSION
        ):
            raise PeerAuthenticationError("Unsupported or malformed AUTH message.")
        if (
            auth_message.get("node_id") != expected_peer_hello["node_id"]
            or auth_message.get("public_key") != expected_peer_hello["public_key"]
        ):
            raise PeerAuthenticationError("AUTH identity does not match the peer HELLO.")
        transcript = cls._transcript(local_hello, expected_peer_hello, local_role)
        expected_hash = hashlib.sha256(transcript).hexdigest()
        if auth_message.get("transcript_sha256") != expected_hash:
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
        if not isinstance(hello, dict):
            raise PeerAuthenticationError("HELLO message must be an object.")
        if hello.get("type") != "HELLO" or hello.get("protocol_version") != cls.PROTOCOL_VERSION:
            raise PeerAuthenticationError("Unsupported or malformed HELLO message.")
        node_id = hello.get("node_id")
        public_key_hex = hello.get("public_key")
        nonce = hello.get("nonce")
        if not all(isinstance(value, str) and value for value in (node_id, public_key_hex, nonce)):
            raise PeerAuthenticationError("HELLO is missing identity or nonce fields.")
        try:
            public_bytes = bytes.fromhex(public_key_hex)
            Ed25519PublicKey.from_public_bytes(public_bytes)
            nonce_bytes = bytes.fromhex(nonce)
        except (ValueError, TypeError) as exc:
            raise PeerAuthenticationError("HELLO public key or nonce is invalid.") from exc
        if len(public_bytes) != 32 or len(nonce_bytes) != 32:
            raise PeerAuthenticationError("HELLO key and nonce must each be 32 bytes.")
        expected_id = "sha256:" + hashlib.sha256(public_bytes).hexdigest()
        if node_id != expected_id:
            raise PeerAuthenticationError("HELLO node ID does not match its public key.")

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
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")

    @classmethod
    def _validate_role(cls, role: str) -> None:
        if role not in cls.ROLES:
            raise PeerAuthenticationError("Role must be 'initiator' or 'responder'.")
