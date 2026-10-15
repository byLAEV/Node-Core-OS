"""Local associations between declared profiles and technical node identities.

A successful association proves control of the node's Ed25519 private key for a
fresh, one-time challenge. It does NOT independently verify a person's civil
identity or prove that the person owns the profile's declared attributes.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
import uuid
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class IdentityAssociationError(RuntimeError):
    """Raised when an association record or proof cannot be accepted."""


class IdentityAssociationStore:
    """Persist profile-to-node associations separately from the profile itself."""

    SCHEMA_VERSION = 1
    PURPOSE = "node-core-os/profile-node-association/v1"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir).expanduser()
        self.identity_dir = self.data_dir / "identity"
        self.path = self.identity_dir / "associations.json"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def issue_challenge(
        self,
        profile_store: Any,
        node_metadata: dict[str, Any],
    ) -> dict[str, str]:
        """Issue a one-time challenge bound to one existing profile and node key."""
        profile = profile_store.load()
        if not isinstance(profile, dict) or not profile.get("identity_id"):
            raise IdentityAssociationError("Create a declared identity profile first.")

        node_id, public_key_hex = self._validate_node_metadata(node_metadata)
        challenge_id = str(uuid.uuid4())
        nonce = secrets.token_hex(32)
        message = self._proof_message(
            challenge_id=challenge_id,
            nonce=nonce,
            profile_identity_id=str(profile["identity_id"]),
            node_id=node_id,
            public_key_hex=public_key_hex,
        )
        state = self._read_state()
        state["pending_challenges"][challenge_id] = {
            "challenge_id": challenge_id,
            "nonce": nonce,
            "profile_identity_id": str(profile["identity_id"]),
            "node_id": node_id,
            "public_key": public_key_hex,
            "issued_at": self._now(),
        }
        self._write_state(state)
        return {
            "challenge_id": challenge_id,
            "message_hex": message.hex(),
            "node_id": node_id,
            "profile_identity_id": str(profile["identity_id"]),
        }

    def complete_association(
        self,
        profile_store: Any,
        challenge_id: str,
        signature_hex: str,
    ) -> dict[str, Any]:
        """Verify and consume a one-time proof, then record control verification."""
        if not isinstance(challenge_id, str) or not challenge_id.strip():
            raise IdentityAssociationError("A challenge identifier is required.")
        try:
            signature = bytes.fromhex(signature_hex)
        except (TypeError, ValueError) as exc:
            raise IdentityAssociationError("Signature must be valid hexadecimal.") from exc

        state = self._read_state()
        pending = state["pending_challenges"].get(challenge_id)
        if not isinstance(pending, dict):
            raise IdentityAssociationError("Challenge is unknown, expired, or already used.")

        profile = profile_store.load()
        if not isinstance(profile, dict):
            raise IdentityAssociationError("The declared identity profile no longer exists.")
        if profile.get("identity_id") != pending.get("profile_identity_id"):
            raise IdentityAssociationError("The profile changed after the challenge was issued.")

        message = self._proof_message(
            challenge_id=pending["challenge_id"],
            nonce=pending["nonce"],
            profile_identity_id=pending["profile_identity_id"],
            node_id=pending["node_id"],
            public_key_hex=pending["public_key"],
        )
        try:
            public_key = Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(pending["public_key"])
            )
            public_key.verify(signature, message)
        except (ValueError, TypeError, InvalidSignature) as exc:
            raise IdentityAssociationError("Node control proof is invalid.") from exc

        association_id = str(uuid.uuid4())
        record = {
            "association_id": association_id,
            "schema_version": self.SCHEMA_VERSION,
            "profile_identity_id": pending["profile_identity_id"],
            "node_id": pending["node_id"],
            "public_key": pending["public_key"],
            "status": "control_verified",
            "verification": "ed25519_challenge_response",
            "created_at": self._now(),
            "revoked_at": None,
        }
        state["associations"].append(record)
        # Consume only after the proof validates; invalid attempts cannot destroy
        # the legitimate pending challenge.
        del state["pending_challenges"][challenge_id]
        self._write_state(state)
        return record.copy()

    def list_associations(
        self, profile_identity_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Return association records, optionally filtered by profile identity ID."""
        state = self._read_state()
        records = state["associations"]
        if profile_identity_id is not None:
            records = [
                item for item in records
                if item.get("profile_identity_id") == profile_identity_id
            ]
        return [item.copy() for item in records]

    def revoke(self, association_id: str) -> dict[str, Any]:
        """Revoke an existing association without deleting its audit record."""
        state = self._read_state()
        for record in state["associations"]:
            if record.get("association_id") == association_id:
                if record.get("status") == "revoked":
                    return record.copy()
                record["status"] = "revoked"
                record["revoked_at"] = self._now()
                self._write_state(state)
                return record.copy()
        raise IdentityAssociationError("Association identifier was not found.")

    def _read_state(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "schema_version": self.SCHEMA_VERSION,
                "associations": [],
                "pending_challenges": {},
            }
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise IdentityAssociationError("Association store is unreadable.") from exc
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != self.SCHEMA_VERSION
            or not isinstance(payload.get("associations"), list)
            or not isinstance(payload.get("pending_challenges"), dict)
        ):
            raise IdentityAssociationError("Association store has an unsupported or invalid format.")
        return payload

    def _write_state(self, state: dict[str, Any]) -> None:
        self.identity_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.identity_dir, 0o700)
        except OSError:
            pass
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".associations-", suffix=".tmp", dir=self.identity_dir
        )
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    @staticmethod
    def _validate_node_metadata(metadata: dict[str, Any]) -> tuple[str, str]:
        if not isinstance(metadata, dict):
            raise IdentityAssociationError("Node metadata must be an object.")
        if metadata.get("schema_version") != 1 or metadata.get("algorithm") != "Ed25519":
            raise IdentityAssociationError("Unsupported technical node identity format.")
        public_key_hex = metadata.get("public_key")
        node_id = metadata.get("node_id")
        if not isinstance(public_key_hex, str) or not isinstance(node_id, str):
            raise IdentityAssociationError("Node metadata lacks its public key or node ID.")
        try:
            public_bytes = bytes.fromhex(public_key_hex)
            Ed25519PublicKey.from_public_bytes(public_bytes)
        except (ValueError, TypeError) as exc:
            raise IdentityAssociationError("Node public key is invalid.") from exc
        expected_node_id = "sha256:" + hashlib.sha256(public_bytes).hexdigest()
        if node_id != expected_node_id:
            raise IdentityAssociationError("Node ID does not match its public key.")
        return node_id, public_key_hex

    @classmethod
    def _proof_message(
        cls,
        *,
        challenge_id: str,
        nonce: str,
        profile_identity_id: str,
        node_id: str,
        public_key_hex: str,
    ) -> bytes:
        payload = {
            "purpose": cls.PURPOSE,
            "challenge_id": challenge_id,
            "nonce": nonce,
            "profile_identity_id": profile_identity_id,
            "node_id": node_id,
            "public_key": public_key_hex,
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
