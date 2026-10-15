"""Genesis manifest loading and deterministic propagation-hash primitives.

These helpers verify the shipped reference and calculate hashes. They do not
implement authenticated acceptance or claim that a peer accepted a hash.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

GENESIS_HASH = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
GENESIS_SCHEMA = "node-core-os-p2p-contracts/manifest/v1"
GENESIS_PATH = Path(__file__).resolve().parents[1] / "genesis-manifest.json"


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    """Serialize JSON deterministically as UTF-8 with sorted keys."""
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def content_hash(payload: dict[str, Any]) -> str:
    """Hash canonical block content, excluding derived hash fields."""
    if not isinstance(payload, dict):
        raise ValueError("Block content must be a JSON object.")
    body = {key: value for key, value in payload.items()
            if key not in {"HL", "HL_hash", "content_hash", "propagation_hash", "derived_hashes"}}
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def next_propagation_hash(previous_hash: str, block_content_hash: str) -> str:
    """Hash two 32-byte SHA-256 digests concatenated in binary form."""
    for label, value in (("previous hash", previous_hash), ("content hash", block_content_hash)):
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"{label} must be a 64-character hexadecimal SHA-256 hash.")
        try:
            decoded = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError(f"{label} is not valid hexadecimal.") from exc
        if len(decoded) != 32:
            raise ValueError(f"{label} must decode to exactly 32 bytes.")
    return hashlib.sha256(bytes.fromhex(previous_hash) + bytes.fromhex(block_content_hash)).hexdigest()


def load_genesis(path: Path | None = None) -> dict[str, Any]:
    """Load and validate the bundled genesis manifest and Bitcoin root reference."""
    manifest_path = path or GENESIS_PATH
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load Node Core P2P Contracts genesis manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("Genesis manifest must be a JSON object.")
    if manifest.get("schema") != GENESIS_SCHEMA:
        raise ValueError("Unsupported genesis manifest schema.")
    if manifest.get("application_id") != "node-core-os-p2p-contracts":
        raise ValueError("Genesis manifest application ID is invalid.")
    if manifest.get("block") != 0 or manifest.get("block_type") != "GENESIS":
        raise ValueError("Genesis manifest must describe logical block 0.")
    if manifest.get("genesis_hash") != GENESIS_HASH:
        raise ValueError("Genesis manifest root hash does not match the configured Bitcoin Mainnet reference.")
    if manifest.get("previous_block_hash") is not None:
        raise ValueError("Genesis manifest cannot have a previous block.")
    reference = manifest.get("references", {}).get("bitcoin_genesis_block", {})
    if reference.get("network") != "Bitcoin Mainnet" or reference.get("block_height") != 0:
        raise ValueError("Bitcoin genesis reference network or height is invalid.")
    if reference.get("block_hash") != GENESIS_HASH:
        raise ValueError("Bitcoin genesis reference hash is invalid.")
    protocol = manifest.get("protocol", {})
    root = protocol.get("root_reference", {})
    initial = protocol.get("initial_acceptance", {})
    if root.get("root_hash") != GENESIS_HASH or initial.get("required_hash") != GENESIS_HASH:
        raise ValueError("Genesis root and initial acceptance reference must match.")
    if manifest.get("status") != "GENESIS_REFERENCE" or manifest.get("requests") != []:
        raise ValueError("Genesis manifest status or request list is invalid.")
    return manifest
