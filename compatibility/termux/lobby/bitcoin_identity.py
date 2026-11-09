"""Local Bitcoin P2WPKH proof gate for the Termux Lobby.

The authenticated HTTPS loopback API may pass a raw HEX scalar to
verify_private_key_and_stage. The scalar is used transiently to derive the
compressed public key and sign a single-use challenge; it is never persisted or
returned. Cleanup is best-effort: Python and cryptographic backend memory cannot
be guaranteed to be zeroized. verify_and_stage also accepts public proof
material produced by an external signer. Only public identity and proof data are
persisted in the local pending record.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import re
from pathlib import Path
import secrets
import tempfile
from cryptography.hazmat.primitives import serialization
import threading
import time
import uuid
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils


BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32_CONST = 1
BECH32_GENERATORS = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
PURPOSE = "Node Core OS byLAEV Bitcoin key-control proof v1"
NETWORK = "mainnet"
ADDRESS_TYPE = "p2wpkh"
CHALLENGE_TTL_SECONDS = 300
PENDING_TTL_SECONDS = 24 * 60 * 60


class BitcoinIdentityError(ValueError):
    """Raised when a Bitcoin identity proof is invalid or cannot be stored."""


def _polymod(values: list[int]) -> int:
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for index, generator in enumerate(BECH32_GENERATORS):
            if (top >> index) & 1:
                checksum ^= generator
    return checksum


def _hrp_expand(hrp: str) -> list[int]:
    return [ord(char) >> 5 for char in hrp] + [0] + [ord(char) & 31 for char in hrp]


def _convert_bits(data: bytes, from_bits: int, to_bits: int, pad: bool = True) -> list[int]:
    accumulator = 0
    bit_count = 0
    result: list[int] = []
    maximum = (1 << to_bits) - 1
    for value in data:
        if value < 0 or (value >> from_bits):
            raise BitcoinIdentityError("Invalid witness program data.")
        accumulator = (accumulator << from_bits) | value
        bit_count += from_bits
        while bit_count >= to_bits:
            bit_count -= to_bits
            result.append((accumulator >> bit_count) & maximum)
    if pad:
        if bit_count:
            result.append((accumulator << (to_bits - bit_count)) & maximum)
    elif bit_count >= from_bits or ((accumulator << (to_bits - bit_count)) & maximum):
        raise BitcoinIdentityError("Invalid witness program padding.")
    return result


def encode_p2wpkh_address(public_key: bytes, network: str = NETWORK) -> str:
    """Derive a mainnet Bech32 P2WPKH address from a compressed secp256k1 key."""
    if network != NETWORK:
        raise BitcoinIdentityError("Only Bitcoin mainnet is enabled for this first-install release.")
    if not isinstance(public_key, bytes) or len(public_key) != 33 or public_key[0] not in (2, 3):
        raise BitcoinIdentityError("A compressed 33-byte secp256k1 public key is required.")
    try:
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), public_key)
    except ValueError as exc:
        raise BitcoinIdentityError("The supplied secp256k1 public key is invalid.") from exc
    try:
        digest = hashlib.new("ripemd160", hashlib.sha256(public_key).digest()).digest()
    except ValueError as exc:
        raise BitcoinIdentityError("RIPEMD-160 is unavailable in this Python runtime.") from exc
    data = [0] + _convert_bits(digest, 8, 5)
    hrp = "bc"
    values = _hrp_expand(hrp) + data + [0] * 6
    polymod = _polymod(values) ^ BECH32_CONST
    checksum = [(polymod >> (5 * (5 - index))) & 31 for index in range(6)]
    return hrp + "1" + "".join(BECH32_CHARSET[value] for value in data + checksum)


def verify_challenge_signature(public_key: bytes, message: bytes, signature: bytes) -> None:
    """Verify DER ECDSA over SHA-256(message), without accepting private key material."""
    if not isinstance(signature, bytes) or not 8 <= len(signature) <= 72:
        raise BitcoinIdentityError("The Bitcoin proof signature has an invalid DER length.")
    try:
        key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), public_key)
        key.verify(signature, hashlib.sha256(message).digest(), ec.ECDSA(utils.Prehashed(hashes.SHA256())))
    except (ValueError, InvalidSignature) as exc:
        raise BitcoinIdentityError("Bitcoin key-control signature is invalid.") from exc


class BitcoinIdentityGate:
    """Issue single-use challenges and persist public-only Bitcoin identity proofs."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = Path(state_dir).expanduser()
        self.pending_path = self.state_dir / "bitcoin-identity-pending.json"
        self._lock = threading.Lock()
        self._challenges: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _normalize_name(value: Any) -> str:
        if not isinstance(value, str):
            raise BitcoinIdentityError("Full name is required.")
        normalized = " ".join(value.split())
        if not 2 <= len(normalized) <= 120:
            raise BitcoinIdentityError("Full name must contain between 2 and 120 characters.")
        if any(ord(char) < 32 or ord(char) == 127 for char in normalized):
            raise BitcoinIdentityError("Full name contains unsupported control characters.")
        return normalized

    @staticmethod
    def _proof_message(challenge_id: str, nonce: str, full_name: str) -> bytes:
        message = (
            PURPOSE + "\n"
            + "challenge_id:" + challenge_id + "\n"
            + "nonce:" + nonce + "\n"
            + "network:" + NETWORK + "\n"
            + "address_type:" + ADDRESS_TYPE + "\n"
            + "full_name_sha256:" + hashlib.sha256(full_name.encode("utf-8")).hexdigest() + "\n"
        )
        return message.encode("utf-8")

    def issue_challenge(self, full_name: Any) -> dict[str, Any]:
        normalized_name = self._normalize_name(full_name)
        challenge_id = str(uuid.uuid4())
        nonce = secrets.token_hex(32)
        issued_at = datetime.now(timezone.utc)
        message = self._proof_message(challenge_id, nonce, normalized_name)
        challenge = {
            "challenge_id": challenge_id,
            "full_name": normalized_name,
            "nonce": nonce,
            "message": message,
            "issued_monotonic": time.monotonic(),
            "expires_at": (issued_at + timedelta(seconds=CHALLENGE_TTL_SECONDS)).isoformat(),
        }
        with self._lock:
            self._prune_challenges_locked()
            self._challenges[challenge_id] = challenge
        return {
            "challenge_id": challenge_id,
            "message": message.decode("utf-8"),
            "network": NETWORK,
            "address_type": ADDRESS_TYPE,
            "expires_at": challenge["expires_at"],
        }

    def _prune_challenges_locked(self) -> None:
        now = time.monotonic()
        expired = [
            key for key, value in self._challenges.items()
            if now - value["issued_monotonic"] > CHALLENGE_TTL_SECONDS
        ]
        for key in expired:
            self._challenges.pop(key, None)

    def verify_and_stage(
        self,
        *,
        challenge_id: Any,
        public_key_hex: Any,
        address: Any,
        signature_hex: Any,
    ) -> dict[str, Any]:
        if not isinstance(challenge_id, str) or not isinstance(public_key_hex, str):
            raise BitcoinIdentityError("Challenge and public key are required.")
        if not isinstance(address, str) or not isinstance(signature_hex, str):
            raise BitcoinIdentityError("Bitcoin address and signature are required.")
        with self._lock:
            self._prune_challenges_locked()
            challenge = self._challenges.pop(challenge_id, None)
        if challenge is None:
            raise BitcoinIdentityError("Bitcoin challenge is unknown, expired, or already used.")

        try:
            public_key = bytes.fromhex(public_key_hex)
            signature = bytes.fromhex(signature_hex)
        except ValueError as exc:
            raise BitcoinIdentityError("Public key and signature must be hexadecimal.") from exc
        if public_key.hex() != public_key_hex.lower():
            raise BitcoinIdentityError("Public key hexadecimal encoding is not canonical.")
        derived_address = encode_p2wpkh_address(public_key)
        if not hmac.compare_digest(derived_address, address):
            raise BitcoinIdentityError("Bitcoin address does not match the supplied public key.")
        message = challenge["message"]
        verify_challenge_signature(public_key, message, signature)

        now = datetime.now(timezone.utc)
        pending = {
            "schema_version": 1,
            "installation_id": str(uuid.uuid4()),
            "entity_id": str(uuid.uuid4()),
            "full_name": challenge["full_name"],
            "identity_status": "declared",
            "bitcoin": {
                "network": NETWORK,
                "address_type": ADDRESS_TYPE,
                "address": derived_address,
                "public_key_hex": public_key.hex(),
            },
            "proof": {
                "method": "node-core-os-bitcoin-key-control/v1",
                "challenge_id": challenge_id,
                "message_sha256": hashlib.sha256(message).hexdigest(),
                "signature_hex": signature.hex(),
                "verified_at": now.isoformat(),
                "status": "control_verified",
            },
            "civil_identity_status": "not_verified",
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=PENDING_TTL_SECONDS)).isoformat(),
        }
        self._write_pending(pending)
        return self.public_status()

    def verify_private_key_and_stage(
        self,
        *,
        challenge_id: Any,
        private_key_hex: Any,
    ) -> dict[str, Any]:
        """Derive and prove a raw private scalar received only by the local Lobby.

        The scalar is never written to disk or returned. The caller must send it
        only to this loopback-bound, authenticated Lobby endpoint. Python cannot
        guarantee zeroization of immutable strings or cryptography backend state;
        this method therefore clears its mutable byte buffer and releases local
        references on a best-effort basis.
        """
        if not isinstance(challenge_id, str):
            raise BitcoinIdentityError("A valid Bitcoin challenge identifier is required.")
        if not isinstance(private_key_hex, str) or len(private_key_hex) != 64:
            raise BitcoinIdentityError("Bitcoin private key must be exactly 64 hexadecimal characters.")
        if any(character not in "0123456789abcdefABCDEF" for character in private_key_hex):
            raise BitcoinIdentityError("Bitcoin private key must contain hexadecimal characters only.")

        with self._lock:
            self._prune_challenges_locked()
            challenge = self._challenges.pop(challenge_id, None)
        if challenge is None:
            raise BitcoinIdentityError("Bitcoin challenge is unknown, expired, or already used.")

        private_key_bytes = bytearray.fromhex(private_key_hex)
        private_key = None
        scalar = int.from_bytes(private_key_bytes, "big")
        for index in range(len(private_key_bytes)):
            private_key_bytes[index] = 0
        private_key_hex = None
        if scalar <= 0 or scalar >= 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141:
            raise BitcoinIdentityError("Bitcoin private key scalar is outside the secp256k1 range.")

        try:
            private_key = ec.derive_private_key(scalar, ec.SECP256K1())
            public_key = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.CompressedPoint,
            )
            derived_address = encode_p2wpkh_address(public_key)
            message = challenge["message"]
            signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
            verify_challenge_signature(public_key, message, signature)
        except (ValueError, TypeError) as exc:
            raise BitcoinIdentityError("Bitcoin private key could not produce a valid mainnet address.") from exc
        finally:
            scalar = 0
            private_key = None

        now = datetime.now(timezone.utc)
        pending = {
            "schema_version": 1,
            "installation_id": str(uuid.uuid4()),
            "entity_id": str(uuid.uuid4()),
            "full_name": challenge["full_name"],
            "identity_status": "declared",
            "bitcoin": {
                "network": NETWORK,
                "address_type": ADDRESS_TYPE,
                "address": derived_address,
                "public_key_hex": public_key.hex(),
            },
            "proof": {
                "method": "node-core-os-local-bitcoin-key-control/v1",
                "challenge_id": challenge_id,
                "message_sha256": hashlib.sha256(message).hexdigest(),
                "signature_hex": signature.hex(),
                "verified_at": now.isoformat(),
                "status": "control_verified",
            },
            "private_key_storage": False,
            "civil_identity_status": "not_verified",
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=PENDING_TTL_SECONDS)).isoformat(),
        }
        self._write_pending(pending)
        return self.public_status()

    def public_status(self) -> dict[str, Any]:
        pending = self.read_pending()
        if pending is None:
            return {"status": "not_verified", "pending": False}
        return {
            "status": "control_verified",
            "pending": True,
            "full_name": pending["full_name"],
            "network": pending["bitcoin"]["network"],
            "address_type": pending["bitcoin"]["address_type"],
            "address": pending["bitcoin"]["address"],
            "installation_id": pending["installation_id"],
            "entity_id": pending["entity_id"],
            "verified_at": pending["proof"]["verified_at"],
            "expires_at": pending["expires_at"],
            "node_id": (pending.get("node_association") or {}).get("node_id"),
            "node_association_status": (
                (pending.get("node_association") or {}).get("status", "not_associated")
            ),
            "node_key_possession_verified": bool(
                (pending.get("node_association") or {}).get("node_key_possession_verified")
            ),
        }

    def record_node_association(
        self,
        *,
        node_id: Any,
        proof_sha256: Any,
    ) -> dict[str, Any]:
        """Record the locally verified NODE ID linked to this Bitcoin proof."""
        if not isinstance(node_id, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", node_id) is None:
            raise BitcoinIdentityError("A canonical SHA-256 Node Core OS identifier is required.")
        if not isinstance(proof_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", proof_sha256) is None:
            raise BitcoinIdentityError("A valid Node ID possession proof digest is required.")

        pending = self.read_pending()
        if pending is None:
            raise BitcoinIdentityError("A non-expired Bitcoin identity proof is required.")
        existing = pending.get("node_association")
        if isinstance(existing, dict):
            existing_node_id = existing.get("node_id")
            if existing_node_id and existing_node_id != node_id:
                raise BitcoinIdentityError(
                    "This Bitcoin identity is already associated with a different NODE ID."
                )
            if existing_node_id == node_id and existing.get("status") == "associated":
                return self.public_status()

        now = datetime.now(timezone.utc).isoformat()
        pending["node_association"] = {
            "node_id": node_id,
            "relationship": "controlled_by",
            "status": "associated",
            "node_key_possession_verified": True,
            "proof_sha256": proof_sha256,
            "verified_at": now,
        }
        self._write_pending(pending)
        return self.public_status()

    def read_pending(self) -> dict[str, Any] | None:
        if self.pending_path.is_symlink() or not self.pending_path.is_file():
            return None
        try:
            payload = json.loads(self.pending_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BitcoinIdentityError("Pending Bitcoin identity record is unreadable.") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise BitcoinIdentityError("Pending Bitcoin identity schema is unsupported.")
        if payload.get("civil_identity_status") != "not_verified":
            raise BitcoinIdentityError("Pending identity verification status is invalid.")
        try:
            expires_at = datetime.fromisoformat(payload["expires_at"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BitcoinIdentityError("Pending Bitcoin proof expiry is invalid.") from exc
        if expires_at <= datetime.now(timezone.utc):
            self.cancel_pending()
            return None
        bitcoin = payload.get("bitcoin")
        proof = payload.get("proof")
        if not isinstance(bitcoin, dict) or not isinstance(proof, dict):
            raise BitcoinIdentityError("Pending Bitcoin proof is incomplete.")
        if bitcoin.get("network") != NETWORK or bitcoin.get("address_type") != ADDRESS_TYPE:
            raise BitcoinIdentityError("Pending Bitcoin proof uses an unsupported network or address type.")
        if proof.get("status") != "control_verified":
            raise BitcoinIdentityError("Pending Bitcoin proof is not verified.")
        return payload

    def cancel_pending(self) -> None:
        if self.pending_path.is_symlink():
            raise BitcoinIdentityError("Refusing to remove a symlink pending identity file.")
        try:
            self.pending_path.unlink(missing_ok=True)
        except OSError as exc:
            raise BitcoinIdentityError("Could not clear pending Bitcoin identity data.") from exc

    def _write_pending(self, payload: dict[str, Any]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.state_dir, 0o700)
        except OSError:
            pass
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".bitcoin-pending-", suffix=".tmp", dir=self.state_dir
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.pending_path)
            try:
                os.chmod(self.pending_path, 0o600)
            except OSError:
                pass
        finally:
            temporary.unlink(missing_ok=True)
