"""Persistent, versioned allowlist of explicitly trusted Node Core OS peers."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class PeerTrustStoreError(RuntimeError):
    """Raised when the peer trust store or a peer certificate is invalid."""


class PeerTrustStore:
    """Persist trusted peer certificates without ever storing private keys."""

    SCHEMA_VERSION = 1

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir).expanduser()
        self.path = self.data_dir / "p2p" / "trusted-peers.json"

    def load(self) -> dict[str, Any]:
        """Load and validate the store. Missing store means an empty allowlist."""
        if not self.path.exists():
            return {"schema_version": self.SCHEMA_VERSION, "peers": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PeerTrustStoreError("Peer trust store is unreadable or invalid JSON.") from exc
        if not isinstance(data, dict) or data.get("schema_version") != self.SCHEMA_VERSION:
            raise PeerTrustStoreError("Unsupported or malformed peer trust store schema.")
        peers = data.get("peers")
        if not isinstance(peers, dict):
            raise PeerTrustStoreError("Peer trust store peers must be an object.")
        for node_id, record in peers.items():
            if not isinstance(record, dict):
                raise PeerTrustStoreError("Peer trust record must be an object.")
            if record.get("node_id") != node_id:
                raise PeerTrustStoreError("Peer trust record key does not match node ID.")
            if record.get("status") not in ("trusted", "revoked"):
                raise PeerTrustStoreError("Peer trust record has an invalid status.")
            pem = record.get("certificate_pem")
            if not isinstance(pem, str):
                raise PeerTrustStoreError("Peer trust record has no PEM certificate.")
            self._validate_certificate(node_id, pem.encode("ascii"), check_validity=False)
        return data

    def add(
        self,
        node_id: str,
        certificate_pem: bytes,
        label: str = "",
        replace_certificate: bool = False,
    ) -> dict[str, str]:
        """Explicitly trust a certificate after matching its Ed25519 key to node_id."""
        self._validate_node_id(node_id)
        self._validate_label(label)
        fingerprint = self._validate_certificate(node_id, certificate_pem, check_validity=True)
        data = self.load()
        existing = data["peers"].get(node_id)
        pem_text = certificate_pem.decode("ascii")
        if existing and existing["status"] == "trusted":
            if existing["certificate_pem"] == pem_text:
                return self._public_record(existing)
            if not replace_certificate:
                raise PeerTrustStoreError(
                    "A different certificate is already trusted for this node; "
                    "use explicit replacement after verifying the peer out of band."
                )
        record = {
            "node_id": node_id,
            "certificate_pem": pem_text,
            "fingerprint_sha256": fingerprint,
            "label": label,
            "status": "trusted",
            "added_at": datetime.now(timezone.utc).isoformat(),
            "revoked_at": None,
        }
        data["peers"][node_id] = record
        self._save(data)
        return self._public_record(record)

    def revoke(self, node_id: str) -> dict[str, str]:
        """Mark a known peer revoked while retaining an audit record."""
        self._validate_node_id(node_id)
        data = self.load()
        record = data["peers"].get(node_id)
        if record is None:
            raise PeerTrustStoreError("Cannot revoke an unknown peer.")
        if record["status"] != "revoked":
            record["status"] = "revoked"
            record["revoked_at"] = datetime.now(timezone.utc).isoformat()
            self._save(data)
        return self._public_record(record)

    def get(self, node_id: str) -> dict[str, str] | None:
        """Return public metadata for a peer, including revoked peers."""
        self._validate_node_id(node_id)
        record = self.load()["peers"].get(node_id)
        return self._public_record(record) if record else None

    def trusted_certificates(self) -> dict[str, bytes]:
        """Return active pinned certificates keyed by node ID for NodePeerService."""
        data = self.load()
        return {
            node_id: record["certificate_pem"].encode("ascii")
            for node_id, record in data["peers"].items()
            if record["status"] == "trusted"
        }

    def list_peers(self) -> list[dict[str, str]]:
        """Return sorted public peer metadata without certificate contents."""
        data = self.load()
        return [
            self._public_record(data["peers"][node_id])
            for node_id in sorted(data["peers"])
        ]

    @staticmethod
    def _validate_node_id(node_id: str) -> None:
        if not isinstance(node_id, str) or len(node_id) != 71 or not node_id.startswith("sha256:"):
            raise PeerTrustStoreError("Node ID must use sha256:<64 lowercase hex characters>.")
        suffix = node_id[7:]
        if any(char not in "0123456789abcdef" for char in suffix):
            raise PeerTrustStoreError("Node ID contains invalid hexadecimal characters.")

    @staticmethod
    def _validate_label(label: str) -> None:
        if not isinstance(label, str) or len(label) > 128 or any(ord(c) < 32 for c in label):
            raise PeerTrustStoreError("Peer label must be text of at most 128 printable characters.")

    @staticmethod
    def _validate_certificate(
        node_id: str, certificate_pem: bytes, check_validity: bool = True
    ) -> str:
        if not isinstance(certificate_pem, bytes) or not certificate_pem:
            raise PeerTrustStoreError("A PEM certificate is required.")
        try:
            cert = x509.load_pem_x509_certificate(certificate_pem)
            public_key = cert.public_key()
            if not isinstance(public_key, Ed25519PublicKey):
                raise PeerTrustStoreError("Peer certificate must contain an Ed25519 public key.")
            raw = public_key.public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
            derived_id = "sha256:" + hashlib.sha256(raw).hexdigest()
            if derived_id != node_id:
                raise PeerTrustStoreError("Certificate public key does not match the node ID.")
            if check_validity:
                now = datetime.now(timezone.utc)
                not_before = getattr(
                    cert, "not_valid_before_utc",
                    cert.not_valid_before.replace(tzinfo=timezone.utc),
                )
                not_after = getattr(
                    cert, "not_valid_after_utc",
                    cert.not_valid_after.replace(tzinfo=timezone.utc),
                )
                if now < not_before or now > not_after:
                    raise PeerTrustStoreError("Peer certificate is outside its validity period.")
            return hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()
        except (ValueError, TypeError, UnicodeError) as exc:
            raise PeerTrustStoreError("Peer certificate is malformed.") from exc

    @staticmethod
    def _public_record(record: dict[str, Any]) -> dict[str, str]:
        return {
            "node_id": record["node_id"],
            "fingerprint_sha256": record["fingerprint_sha256"],
            "label": record["label"],
            "status": record["status"],
            "added_at": record["added_at"],
            "revoked_at": record["revoked_at"] or "",
        }

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".trusted-peers-", suffix=".tmp", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        finally:
            if temporary.exists():
                temporary.unlink()
