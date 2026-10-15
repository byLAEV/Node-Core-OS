"""Persistent cryptographic identity for a Node Core OS installation.

The technical node identity is independent of the user-declared identity profile.
Private keys are stored as unencrypted PEM files protected by filesystem permissions;
this is not protection against a compromised process running as the same user.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class NodeIdentityError(RuntimeError):
    """Raised when a saved technical node identity is missing or invalid."""


class NodeIdentityStore:
    """Create, load, and verify one persistent Ed25519 identity per data directory."""

    SCHEMA_VERSION = 1
    ALGORITHM = "Ed25519"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir).expanduser()
        self.identity_dir = self.data_dir / "identity"
        self.private_dir = self.identity_dir / "private"
        self.metadata_path = self.identity_dir / "node.json"
        self.private_key_path = self.private_dir / "node.key"

    def initialize(self) -> dict[str, Any]:
        """Create an identity only when neither identity file exists; otherwise validate it."""
        metadata_exists = self.metadata_path.exists()
        key_exists = self.private_key_path.exists()

        if metadata_exists or key_exists:
            if not metadata_exists or not key_exists:
                raise NodeIdentityError(
                    "Technical identity is incomplete; refusing to generate a replacement."
                )
            return self.load()

        self.identity_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._restrict_directory(self.identity_dir)
        self._restrict_directory(self.private_dir)

        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        metadata = {
            "schema_version": self.SCHEMA_VERSION,
            "algorithm": self.ALGORITHM,
            "node_id": self._node_id(public_bytes),
            "public_key": public_bytes.hex(),
        }

        # Write the secret first. If interrupted between writes, the next startup
        # detects the incomplete pair and fails closed instead of rotating identity.
        self._atomic_write(self.private_key_path, private_pem, 0o600)
        self._atomic_write(
            self.metadata_path,
            (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            0o600,
        )
        return self.load()

    def load(self) -> dict[str, Any]:
        """Load and cross-check both files without creating or repairing anything."""
        if not self.metadata_path.is_file() or not self.private_key_path.is_file():
            raise NodeIdentityError("Technical identity files are missing.")

        try:
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise NodeIdentityError("Technical identity metadata is unreadable.") from exc

        if not isinstance(metadata, dict):
            raise NodeIdentityError("Technical identity metadata must be a JSON object.")
        if metadata.get("schema_version") != self.SCHEMA_VERSION:
            raise NodeIdentityError("Unsupported technical identity schema version.")
        if metadata.get("algorithm") != self.ALGORITHM:
            raise NodeIdentityError("Unsupported technical identity algorithm.")

        try:
            private_key = serialization.load_pem_private_key(
                self.private_key_path.read_bytes(), password=None
            )
        except (OSError, ValueError, TypeError) as exc:
            raise NodeIdentityError("Technical private key is unreadable or invalid.") from exc

        if not isinstance(private_key, Ed25519PrivateKey):
            raise NodeIdentityError("Technical private key is not Ed25519.")

        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        expected_public_hex = public_bytes.hex()
        expected_node_id = self._node_id(public_bytes)
        if metadata.get("public_key") != expected_public_hex:
            raise NodeIdentityError("Public key does not match the private key.")
        if metadata.get("node_id") != expected_node_id:
            raise NodeIdentityError("Node identifier does not match the public key.")

        return metadata

    def sign(self, message: bytes) -> bytes:
        """Sign bytes with this node's private key without exposing the key."""
        self.load()
        private_key = serialization.load_pem_private_key(
            self.private_key_path.read_bytes(), password=None
        )
        if not isinstance(private_key, Ed25519PrivateKey):
            raise NodeIdentityError("Technical private key is not Ed25519.")
        return private_key.sign(message)

    @staticmethod
    def verify(public_key_hex: str, message: bytes, signature: bytes) -> bool:
        """Verify a signature against a raw Ed25519 public key encoded as hex."""
        try:
            public_bytes = bytes.fromhex(public_key_hex)
            public_key = Ed25519PublicKey.from_public_bytes(public_bytes)
            public_key.verify(signature, message)
        except (ValueError, TypeError):
            return False
        except Exception as exc:
            # InvalidSignature is intentionally converted to a verification result.
            from cryptography.exceptions import InvalidSignature
            if isinstance(exc, InvalidSignature):
                return False
            raise
        return True

    @staticmethod
    def _node_id(public_bytes: bytes) -> str:
        return "sha256:" + hashlib.sha256(public_bytes).hexdigest()

    @staticmethod
    def _restrict_directory(path: Path) -> None:
        try:
            os.chmod(path, 0o700)
        except OSError:
            # Some filesystems do not support POSIX permission changes.
            pass

    @staticmethod
    def _atomic_write(path: Path, content: bytes, mode: int) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}-", suffix=".tmp", dir=path.parent
        )
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
