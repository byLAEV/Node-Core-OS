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
    if any(ord(character) < 32 and character not in "\t\n\r" for character in content):
        raise ValueError("Document text contains terminal control characters; remove them and try again.")
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


def validate_ots_metadata(original_path: Path, metadata: dict[str, Any] | None, *, trusted_verified_result: bool = False) -> dict[str, Any] | None:
    """Validate that an OTS report refers to these exact original bytes.

    Reports are user-editable JSON, so their presence is not trusted as proof by
    itself. This checks the claimed original digest, expected proof filename, and
    known status vocabulary. A VERIFIED claim is rechecked with the official CLI
    by the command layer before it is accepted into a generated package.
    """
    if metadata is None:
        return None
    original = Path(original_path).expanduser()
    if not original.is_file():
        raise ValueError(f"Original document does not exist: {original}")
    expected_digest = sha256_bytes(original.read_bytes())
    reported_digest = metadata.get("original_sha256")
    if not isinstance(reported_digest, str) or reported_digest.lower() != expected_digest:
        raise ValueError(
            "OpenTimestamps report SHA-256 does not match the current original document."
        )

    expected_proof_name = original.name + ".ots"
    supplied_proof = metadata.get("proof_file")
    if not isinstance(supplied_proof, str) or Path(supplied_proof).name != expected_proof_name:
        raise ValueError(
            f"OpenTimestamps report must refer to the expected proof filename: {expected_proof_name}"
        )

    proof_path = Path(str(original) + ".ots")
    if not proof_path.is_file() or proof_path.stat().st_size == 0:
        raise ValueError("OpenTimestamps report supplied, but the corresponding .ots proof is missing or empty.")

    allowed_statuses = {
        "WAITING_FOR_BITCOIN",
        "ANCHOR_AVAILABLE",
        "VERIFIED",
        "NETWORK_ERROR",
        "PROOF_ERROR",
        "NOT_CHECKED",
    }
    status = metadata.get("status")
    if status not in allowed_statuses:
        raise ValueError("OpenTimestamps report has an unknown or unsupported status.")
    verification = metadata.get("proof_verification")
    if status == "VERIFIED" and not trusted_verified_result:
        raise ValueError(
            "A JSON report cannot establish VERIFIED status by itself; run the official OpenTimestamps check first."
        )
    if status == "VERIFIED" and verification != "SUCCESS":
        raise ValueError("OpenTimestamps report has an inconsistent VERIFIED status.")
    if verification == "SUCCESS" and status != "VERIFIED":
        raise ValueError("OpenTimestamps report has an inconsistent successful verification result.")

    # Keep output useful but avoid publishing absolute local filesystem paths.
    sanitized = dict(metadata)
    sanitized["proof_file"] = expected_proof_name
    for key in ("stdout", "stderr"):
        value = sanitized.get(key)
        if isinstance(value, str):
            sanitized[key] = value.replace(str(original), original.name).replace(
                str(Path(str(original) + ".ots")), expected_proof_name
            )
    return sanitized


def build_transparent_package(
    *,
    original_path: Path,
    identity_profile: dict[str, Any] | None,
    node_id: str | None,
    ots_metadata: dict[str, Any] | None = None,
    trusted_verified_result: bool = False,
) -> dict[str, Any]:
    """Build a transparent package model including the complete original text.

    This function does not submit to OpenTimestamps or publish to IPFS. Callers
    must pass actual metadata obtained from the official client; absent data stays
    explicitly unknown.
    """
    original = Path(original_path).expanduser()
    raw = original.read_bytes()
    try:
        original_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("HashPaper currently packages UTF-8 text/Markdown documents only.") from exc
    if any(ord(character) < 32 and character not in "\t\n\r" for character in original_text):
        raise ValueError("Original document contains terminal control characters; clean or recreate it before packaging.")

    validated_metadata = validate_ots_metadata(original, ots_metadata, trusted_verified_result=trusted_verified_result)
    metadata = validated_metadata or {}
    proof_path = Path(str(original) + ".ots")
    proof_exists = proof_path.is_file() and proof_path.stat().st_size > 0
    proof_bytes = proof_path.read_bytes() if proof_exists else b""
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
            "proof_file": Path(str(metadata.get("proof_file"))).name if metadata.get("proof_file") else (proof_path.name if proof_exists else None),
            "proof_exists": proof_exists,
            "proof_size_bytes": len(proof_bytes) if proof_exists else None,
            "proof_sha256": sha256_bytes(proof_bytes) if proof_exists else None,
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
            "block_height": metadata.get("bitcoin_block_height") if metadata.get("status") == "VERIFIED" and trusted_verified_result else None,
            "block_hash": None,
            "block_timestamp": None,
            "attestation_verification": "VERIFIED_BY_OFFICIAL_OTS_CLIENT" if metadata.get("status") == "VERIFIED" and trusted_verified_result else "NOT_CHECKED",
            "chain_height": None,
            "confirmations": None,
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
