"""Canonical signed presence manifests for the local Node Core OS network.

A manifest is unanimous only when every node listed in its roster has supplied
a valid Ed25519 signature over the exact same canonical roster. Discovery
announcements alone are not consensus votes.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Mapping

from node_core.identity.node_identity import NodeIdentityStore

SCHEMA_VERSION = 1
MAX_NODES = 256


class PresenceManifestError(ValueError):
    """Raised when a presence manifest is malformed or not unanimous."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def create_manifest_body(
    nodes: list[Mapping[str, str]], *, epoch: int | None = None,
    created_at: int | None = None,
) -> dict[str, Any]:
    """Create the immutable roster all participating nodes must sign."""
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_NODES:
        raise PresenceManifestError("Roster must contain between 1 and 256 nodes.")
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for node in nodes:
        if not isinstance(node, Mapping):
            raise PresenceManifestError("Every roster entry must be an object.")
        node_id = node.get("node_id")
        public_key = node.get("public_key")
        if not isinstance(node_id, str) or not node_id.startswith("sha256:") or len(node_id) != 71:
            raise PresenceManifestError("Invalid node ID in roster.")
        if not isinstance(public_key, str) or len(public_key) != 64:
            raise PresenceManifestError("Invalid public key in roster.")
        try:
            public_bytes = bytes.fromhex(public_key)
        except ValueError as exc:
            raise PresenceManifestError("Public key must be hexadecimal.") from exc
        expected_id = "sha256:" + hashlib.sha256(public_bytes).hexdigest()
        if expected_id != node_id:
            raise PresenceManifestError("Node ID does not match its public key.")
        if node_id in seen:
            raise PresenceManifestError("Duplicate node in roster.")
        seen.add(node_id)
        normalized.append({"node_id": node_id, "public_key": public_key})
    normalized.sort(key=lambda entry: entry["node_id"])
    return {
        "schema_version": SCHEMA_VERSION,
        "epoch": int(time.time() if epoch is None else epoch),
        "created_at": int(time.time() if created_at is None else created_at),
        "nodes": normalized,
    }


def sign_manifest(identity_store: NodeIdentityStore, body: Mapping[str, Any]) -> dict[str, str]:
    """Sign a canonical roster only if the signer is explicitly in that roster."""
    identity = identity_store.initialize()
    node_id = identity["node_id"]
    expected = next(
        (node for node in body.get("nodes", []) if node.get("node_id") == node_id),
        None,
    )
    if expected is None or expected.get("public_key") != identity["public_key"]:
        raise PresenceManifestError("Signer is not present in the exact manifest roster.")
    signature = identity_store.sign(canonical_json(dict(body)))
    import base64
    return {"node_id": node_id, "signature": base64.b64encode(signature).decode("ascii")}


def verify_manifest(
    body: Mapping[str, Any], signatures: list[Mapping[str, str]]
) -> dict[str, Any]:
    """Verify unanimity: exactly one valid signature from every roster member."""
    import base64
    if not isinstance(body, Mapping) or set(body) != {
        "schema_version", "epoch", "created_at", "nodes"
    }:
        raise PresenceManifestError("Manifest body schema is invalid.")
    if body.get("schema_version") != SCHEMA_VERSION:
        raise PresenceManifestError("Unsupported manifest schema version.")
    rebuilt = create_manifest_body(
        body.get("nodes"), epoch=body.get("epoch"), created_at=body.get("created_at")
    )
    if canonical_json(rebuilt) != canonical_json(dict(body)):
        raise PresenceManifestError("Manifest roster is not canonical.")
    if not isinstance(signatures, list):
        raise PresenceManifestError("Manifest signatures must be a list.")
    expected = {node["node_id"]: node["public_key"] for node in rebuilt["nodes"]}
    verified: set[str] = set()
    message = canonical_json(rebuilt)
    for entry in signatures:
        if not isinstance(entry, Mapping) or set(entry) != {"node_id", "signature"}:
            raise PresenceManifestError("Malformed manifest signature entry.")
        node_id = entry["node_id"]
        if node_id not in expected or node_id in verified:
            raise PresenceManifestError("Unknown or duplicate manifest signer.")
        try:
            signature = base64.b64decode(entry["signature"], validate=True)
        except (ValueError, TypeError) as exc:
            raise PresenceManifestError("Signature encoding is invalid.") from exc
        if not NodeIdentityStore.verify(expected[node_id], message, signature):
            raise PresenceManifestError(f"Invalid signature from {node_id}.")
        verified.add(node_id)
    missing = sorted(set(expected) - verified)
    if missing:
        raise PresenceManifestError(
            "Manifest is not unanimous; missing signatures from: " + ", ".join(missing)
        )
    digest = hashlib.sha256(message).hexdigest()
    return {
        "unanimous": True,
        "node_count": len(expected),
        "manifest_sha256": digest,
        "signer_node_ids": sorted(verified),
    }
