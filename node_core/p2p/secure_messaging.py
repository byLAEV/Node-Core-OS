"""Hybrid RSA-3072/AES-256-GCM P2P messaging with RSA-PSS signatures.

The existing Ed25519 node identity remains authoritative for node IDs and session
authentication. RSA keys are separate message-encryption/signature keys and must
be pinned out-of-band to a node ID; never trust a key merely because a packet
contains it.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from node_core.identity.node_identity import NodeIdentityStore


class SecureMessagingError(RuntimeError):
    """Raised when secure message creation, verification, or opening fails."""


def _canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _b64e(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _b64d(value: str, field: str) -> bytes:
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeError, AttributeError) as exc:
        raise SecureMessagingError(f"Invalid base64 field: {field}.") from exc


class NodeRSAIdentityStore:
    """Persistent RSA-3072 message keypair separate from the Ed25519 node identity."""

    SCHEMA_VERSION = 1
    ALGORITHM = "RSA-3072"

    def __init__(self, identity_store: NodeIdentityStore) -> None:
        self.identity_store = identity_store
        self.identity_dir = identity_store.identity_dir
        self.private_dir = identity_store.private_dir
        self.private_key_path = self.private_dir / "message-rsa.key"
        self.metadata_path = self.identity_dir / "message-rsa.json"

    def initialize(self) -> dict[str, Any]:
        """Create the RSA pair once; refuse incomplete or mismatched existing keys."""
        self.identity_store.initialize()
        if self.private_key_path.exists() or self.metadata_path.exists():
            if not self.private_key_path.is_file() or not self.metadata_path.is_file():
                raise SecureMessagingError("RSA message identity is incomplete; refusing key rotation.")
            return self.load()
        self.private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.identity_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._restrict_directory(self.private_dir)
        self._restrict_directory(self.identity_dir)
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("ascii")
        metadata = {
            "schema_version": self.SCHEMA_VERSION,
            "algorithm": self.ALGORITHM,
            "node_id": self.identity_store.initialize()["node_id"],
            "public_key_pem": public_pem,
            "public_key_sha256": hashlib.sha256(public_pem.encode("ascii")).hexdigest(),
        }
        private_pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        self._atomic_write(self.private_key_path, private_pem, 0o600)
        self._atomic_write(
            self.metadata_path,
            (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            0o600,
        )
        return self.load()

    def load(self) -> dict[str, Any]:
        """Validate the RSA private/public pair and its association with the Ed25519 node ID."""
        try:
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            private_key = serialization.load_pem_private_key(self.private_key_path.read_bytes(), password=None)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
            raise SecureMessagingError("RSA message identity files are missing or invalid.") from exc
        if not isinstance(metadata, dict) or metadata.get("schema_version") != self.SCHEMA_VERSION:
            raise SecureMessagingError("Unsupported RSA message identity metadata.")
        if metadata.get("algorithm") != self.ALGORITHM:
            raise SecureMessagingError("Unsupported RSA message identity algorithm.")
        if not isinstance(private_key, rsa.RSAPrivateKey) or private_key.key_size != 3072:
            raise SecureMessagingError("Message private key must be RSA-3072.")
        current_node_id = self.identity_store.initialize()["node_id"]
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("ascii")
        if metadata.get("node_id") != current_node_id:
            raise SecureMessagingError("RSA message key is bound to a different Ed25519 node ID.")
        if metadata.get("public_key_pem") != public_pem:
            raise SecureMessagingError("RSA public key does not match the private key.")
        if metadata.get("public_key_sha256") != hashlib.sha256(public_pem.encode("ascii")).hexdigest():
            raise SecureMessagingError("RSA public key fingerprint does not match metadata.")
        return metadata

    def public_key_pem(self) -> bytes:
        return self.load()["public_key_pem"].encode("ascii")

    def private_key(self) -> rsa.RSAPrivateKey:
        self.load()
        key = serialization.load_pem_private_key(self.private_key_path.read_bytes(), password=None)
        if not isinstance(key, rsa.RSAPrivateKey):
            raise SecureMessagingError("Message private key is not RSA.")
        return key

    @staticmethod
    def _restrict_directory(path: Path) -> None:
        try:
            os.chmod(path, 0o700)
        except OSError:
            pass

    @staticmethod
    def _atomic_write(path: Path, content: bytes, mode: int) -> None:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", suffix=".tmp", dir=path.parent)
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, mode)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
            try:
                os.chmod(path, mode)
            except OSError:
                pass
        finally:
            if temporary_path.exists():
                temporary_path.unlink()


def _load_rsa_public_key(public_key_pem: bytes | str) -> rsa.RSAPublicKey:
    try:
        raw = public_key_pem.encode("ascii") if isinstance(public_key_pem, str) else public_key_pem
        key = serialization.load_pem_public_key(raw)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise SecureMessagingError("Invalid RSA public key.") from exc
    if not isinstance(key, rsa.RSAPublicKey) or key.key_size != 3072:
        raise SecureMessagingError("Trusted message public key must be RSA-3072.")
    return key


def _message_aad(message_id: str, sender_node_id: str, recipient_node_id: str) -> bytes:
    return _canonical_json({
        "version": 1, "type": "MESSAGE", "message_id": message_id,
        "sender_node_id": sender_node_id, "recipient_node_id": recipient_node_id,
    })


def _envelope_signing_bytes(envelope: dict[str, Any]) -> bytes:
    return _canonical_json({key: value for key, value in envelope.items() if key != "signature"})


def seal_message(
    sender: NodeRSAIdentityStore,
    recipient_node_id: str,
    recipient_public_key_pem: bytes | str,
    message_id: str,
    text: str,
) -> dict[str, Any]:
    """Encrypt UTF-8 text for a pinned recipient and sign the full envelope with RSA-PSS."""
    if not isinstance(text, str) or not text or len(text.encode("utf-8")) > 16_384:
        raise SecureMessagingError("Message text must contain 1 to 16384 UTF-8 bytes.")
    if not isinstance(message_id, str) or not message_id or len(message_id) > 128:
        raise SecureMessagingError("Invalid message ID.")
    sender_metadata = sender.initialize()
    sender_node_id = sender_metadata["node_id"]
    recipient_key = _load_rsa_public_key(recipient_public_key_pem)
    message_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    aad = _message_aad(message_id, sender_node_id, recipient_node_id)
    ciphertext = AESGCM(message_key).encrypt(nonce, text.encode("utf-8"), aad)
    wrapped_key = recipient_key.encrypt(
        message_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )
    envelope: dict[str, Any] = {
        "version": 1,
        "type": "MESSAGE",
        "message_id": message_id,
        "sender_node_id": sender_node_id,
        "recipient_node_id": recipient_node_id,
        "sender_rsa_public_key": sender_metadata["public_key_pem"],
        "wrapped_key": _b64e(wrapped_key),
        "nonce": _b64e(nonce),
        "ciphertext": _b64e(ciphertext),
    }
    envelope["signature"] = _b64e(sender.private_key().sign(
        _envelope_signing_bytes(envelope),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    ))
    return envelope


def open_message(
    recipient: NodeRSAIdentityStore,
    envelope: dict[str, Any],
    expected_sender_node_id: str,
    trusted_sender_public_key_pem: bytes | str,
) -> str:
    """Verify pinned sender key and RSA-PSS signature before decrypting AES-GCM payload."""
    if not isinstance(envelope, dict) or envelope.get("version") != 1 or envelope.get("type") != "MESSAGE":
        raise SecureMessagingError("Unsupported secure message envelope.")
    if envelope.get("sender_node_id") != expected_sender_node_id:
        raise SecureMessagingError("Message sender node ID does not match the authenticated peer.")
    recipient_node_id = recipient.initialize()["node_id"]
    if envelope.get("recipient_node_id") != recipient_node_id:
        raise SecureMessagingError("Message is addressed to a different node.")
    sender_key = _load_rsa_public_key(trusted_sender_public_key_pem)
    try:
        embedded_key = _load_rsa_public_key(envelope["sender_rsa_public_key"])
        embedded_der = embedded_key.public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        pinned_der = sender_key.public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        if embedded_der != pinned_der:
            raise SecureMessagingError("Envelope RSA key differs from the pinned sender key.")
        signature = _b64d(envelope["signature"], "signature")
        sender_key.verify(
            signature, _envelope_signing_bytes(envelope),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        message_id = envelope["message_id"]
        if not isinstance(message_id, str) or not message_id or len(message_id) > 128:
            raise SecureMessagingError("Invalid message ID.")
        nonce = _b64d(envelope["nonce"], "nonce")
        if len(nonce) != 12:
            raise SecureMessagingError("AES-GCM nonce must be 12 bytes.")
        wrapped_key = _b64d(envelope["wrapped_key"], "wrapped_key")
        ciphertext = _b64d(envelope["ciphertext"], "ciphertext")
        if len(ciphertext) > 16_400:
            raise SecureMessagingError("Encrypted message exceeds the permitted size.")
        message_key = recipient.private_key().decrypt(
            wrapped_key,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        )
        if len(message_key) != 32:
            raise SecureMessagingError("Unwrapped AES key has an invalid length.")
        plaintext = AESGCM(message_key).decrypt(
            nonce, ciphertext, _message_aad(message_id, expected_sender_node_id, recipient_node_id)
        )
        return plaintext.decode("utf-8")
    except SecureMessagingError:
        raise
    except (KeyError, TypeError, ValueError, UnicodeError, InvalidSignature, InvalidTag) as exc:
        raise SecureMessagingError("Secure message authentication or decryption failed.") from exc


def create_ack(
    receiver: NodeRSAIdentityStore, sender_node_id: str, message_id: str
) -> dict[str, Any]:
    """Create a signed receipt after the application has accepted a message."""
    metadata = receiver.initialize()
    payload: dict[str, Any] = {
        "version": 1,
        "type": "MESSAGE_ACK",
        "message_id": message_id,
        "sender_node_id": sender_node_id,
        "receiver_node_id": metadata["node_id"],
        "status": "accepted",
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    payload["signature"] = _b64e(receiver.private_key().sign(
        _canonical_json(payload),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    ))
    return payload


def verify_ack(
    ack: dict[str, Any],
    expected_sender_node_id: str,
    expected_receiver_node_id: str,
    expected_message_id: str,
    trusted_receiver_public_key_pem: bytes | str,
) -> bool:
    """Return True only for a correctly signed receipt matching this exact message."""
    if not isinstance(ack, dict):
        return False
    try:
        if (
            ack.get("version") != 1 or ack.get("type") != "MESSAGE_ACK"
            or ack.get("status") != "accepted"
            or ack.get("sender_node_id") != expected_sender_node_id
            or ack.get("receiver_node_id") != expected_receiver_node_id
            or ack.get("message_id") != expected_message_id
            or not isinstance(ack.get("received_at"), str)
            or len(ack["received_at"]) > 64
        ):
            return False
        signature = _b64d(ack["signature"], "signature")
        payload = {key: value for key, value in ack.items() if key != "signature"}
        _load_rsa_public_key(trusted_receiver_public_key_pem).verify(
            signature, _canonical_json(payload),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
    except (KeyError, TypeError, ValueError, SecureMessagingError, InvalidSignature):
        return False
    return True
