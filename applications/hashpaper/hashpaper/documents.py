"""Local-first document and transparent package primitives for HashPaper."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

SCHEMA_VERSION = 1
IDENTITY_FIELDS = (
    "schema_version",
    "identity_id",
    "full_name",
    "alias",
    "nationality",
    "issuing_country",
    "document_type",
    "document_number",
    "birth_date",
    "height_cm",
    "gender",
    "identity_status",
    "node_id",
    "created_at",
    "updated_at",
)


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact input bytes."""
    return hashlib.sha256(data).hexdigest()


def read_identity_fields(profile: dict[str, Any]) -> dict[str, Any]:
    """Return the known profile fields without inventing missing values."""
    return {key: profile.get(key) for key in IDENTITY_FIELDS}


def write_original(path: Path, content: str) -> dict[str, Any]:
    """Create an original UTF-8 text document without overwriting an existing file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8")
    descriptor: int | None = None
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise FileExistsError(f"Original document already exists; choose a new filename: {target}")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return {
        "filename": target.name,
        "format": target.suffix.lstrip(".") or "text",
        "size_bytes": len(data),
        "hash_algorithm": "sha256",
        "sha256": sha256_bytes(data),
        "integrity": "HASHED",
    }


def build_transparent_package(
    *,
    original_path: Path,
    identity_profile: dict[str, Any] | None,
    node_id: str | None,
    ots_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a transparent package model including the complete original text.

    This function does not submit to OpenTimestamps or publish to IPFS. Callers
    must pass actual metadata obtained from the official client; absent data stays
    explicitly unknown.
    """
    original = Path(original_path)
    raw = original.read_bytes()
    try:
        original_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("HashPaper currently packages UTF-8 text/Markdown documents only.") from exc

    metadata = ots_metadata or {}
    return {
        "application": "HashPaper for Node Core OS",
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "encryption": {"implemented": False, "status": "NOT_IMPLEMENTED"},
        "identity": {
            "status": (identity_profile or {}).get("identity_status", "NOT_ASSOCIATED"),
            "fields": read_identity_fields(identity_profile or {}),
            "verification": "NOT_VERIFIED_BY_HASHPAPER",
        },
        "node": {"peer_id": node_id, "verification": "TECHNICAL_IDENTIFIER_ONLY"},
        "document": {
            "filename": original.name,
            "format": original.suffix.lstrip(".") or "text",
            "size_bytes": len(raw),
            "hash_algorithm": "sha256",
            "sha256": sha256_bytes(raw),
            "integrity": "HASHED",
            "original_text": original_text,
        },
        "opentimestamps": {
            "client": "official ots client",
            "proof_file": metadata.get("proof_file"),
            "status": metadata.get("status", "NOT_SUBMITTED"),
            "proof_verification": metadata.get("proof_verification", "NOT_CHECKED"),
            "operation": metadata.get("operation"),
            "return_code": metadata.get("return_code"),
            "stdout": metadata.get("stdout", ""),
            "stderr": metadata.get("stderr", ""),
            "calendars": metadata.get("calendars", []),
        },
        "bitcoin": {
            "network": metadata.get("network"),
            "block_height": metadata.get("bitcoin_block_height", metadata.get("block_height")),
            "block_hash": metadata.get("block_hash"),
            "block_timestamp": metadata.get("block_timestamp"),
            "attestation_verification": metadata.get("attestation_verification", "NOT_CHECKED"),
            "chain_height": metadata.get("chain_height"),
            "confirmations": metadata.get("confirmations"),
        },
        "publication": {"ipfs_cid": None, "pin_status": "NOT_PUBLISHED"},
    }


def write_package(path: Path, package: dict[str, Any]) -> None:
    """Write a JSON package atomically, without replacing the original document."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".hashpaper-", suffix=".tmp", dir=target.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(package, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, target)
        os.chmod(target, 0o600)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
