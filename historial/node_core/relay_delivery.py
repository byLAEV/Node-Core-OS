"""Authenticated relay request validation and durable local receipt handling."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "node-core-os/relay-delivery/v1"
_RUN_ID = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    if not isinstance(value, dict):
        raise ValueError("JSON payload must be an object.")
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def decode_key(key_hex: str) -> bytes:
    if not isinstance(key_hex, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", key_hex):
        raise ValueError("NODE_CORE_RELAY_HMAC_KEY must be exactly 64 hexadecimal characters (32 bytes).")
    return bytes.fromhex(key_hex)


def create_request(run_id: str, payload: dict[str, Any], key_hex: str) -> dict[str, Any]:
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise ValueError("run_id contains unsupported characters or has an invalid length.")
    key = decode_key(key_hex)
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    unsigned = {
        "schema": SCHEMA,
        "run_id": run_id,
        "payload": payload,
        "payload_sha256": digest,
    }
    signature = hmac.new(key, canonical_json_bytes(unsigned), hashlib.sha256).hexdigest()
    return {**unsigned, "hmac_sha256": signature}


def verify_request(envelope: dict[str, Any], key_hex: str) -> dict[str, Any]:
    if not isinstance(envelope, dict) or envelope.get("schema") != SCHEMA:
        raise ValueError("Unsupported or malformed relay request schema.")
    run_id = envelope.get("run_id")
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise ValueError("Relay request run_id is invalid.")
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Relay request payload must be a JSON object.")
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    if not hmac.compare_digest(str(envelope.get("payload_sha256", "")), digest):
        raise ValueError("Relay payload SHA-256 mismatch.")
    unsigned = {key: envelope[key] for key in ("schema", "run_id", "payload", "payload_sha256")}
    expected = hmac.new(decode_key(key_hex), canonical_json_bytes(unsigned), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(envelope.get("hmac_sha256", "")), expected):
        raise ValueError("Relay request HMAC verification failed.")
    return {"run_id": run_id, "payload": payload, "payload_sha256": digest}


def persist_and_sign_receipt(
    data_dir: Path, verified: dict[str, Any], identity_store: Any
) -> dict[str, Any]:
    """Persist a verified payload atomically, then sign a receipt with this node's Ed25519 key."""
    run_id = verified["run_id"]
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("Invalid run_id.")
    inbox = Path(data_dir).expanduser() / "storage" / "relay" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(inbox, 0o700)
    except OSError:
        pass
    target = inbox / f"{run_id}.json"
    stored = {
        "schema": SCHEMA,
        "run_id": run_id,
        "payload": verified["payload"],
        "payload_sha256": verified["payload_sha256"],
        "received_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    encoded = canonical_json_bytes(stored) + b"\n"
    if target.exists():
        if target.read_bytes() != encoded:
            # A retry may arrive at a later timestamp; compare the immutable content instead.
            try:
                existing = json.loads(target.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError("Existing relay inbox file is unreadable; refusing overwrite.") from exc
            if (existing.get("run_id") != run_id or
                    existing.get("payload_sha256") != verified["payload_sha256"] or
                    existing.get("payload") != verified["payload"]):
                raise RuntimeError("run_id already exists with different content; refusing overwrite.")
            stored = existing
            encoded = canonical_json_bytes(stored) + b"\n"
    else:
        fd, temporary = tempfile.mkstemp(prefix=f".{run_id}-", suffix=".tmp", dir=inbox)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            # A hard link publishes the fully-written file atomically without
            # replacing a file created concurrently for the same run ID.
            try:
                os.link(temporary, target)
            except FileExistsError:
                try:
                    existing = json.loads(target.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise RuntimeError("Concurrent relay inbox file is unreadable; refusing overwrite.") from exc
                if (existing.get("run_id") != run_id or
                        existing.get("payload_sha256") != verified["payload_sha256"] or
                        existing.get("payload") != verified["payload"]):
                    raise RuntimeError("run_id already exists with different content; refusing overwrite.")
                stored = existing
            else:
                try:
                    os.chmod(target, 0o600)
                except OSError:
                    pass
                directory_fd = os.open(inbox, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    metadata = identity_store.initialize()
    receipt = {
        "schema": SCHEMA,
        "status": "persisted",
        "run_id": run_id,
        "payload_sha256": verified["payload_sha256"],
        "node_id": metadata["node_id"],
        "public_key": metadata["public_key"],
        "persisted_path": str(target),
        "received_at_utc": stored["received_at_utc"],
    }
    signature = identity_store.sign(canonical_json_bytes(receipt)).hex()
    return {**receipt, "signature_ed25519": signature}
