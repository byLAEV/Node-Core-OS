"""Signed LAN discovery announcements for native Node Core OS P2P.

This module defines and validates the announcement format only. Network sockets,
peer trust decisions, and authenticated sessions remain separate responsibilities.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import ipaddress
import json
import time
from typing import Any

from node_core.identity.node_identity import NodeIdentityStore


MAX_ANNOUNCEMENT_BYTES = 4096
DISCOVERY_PROTOCOL_VERSION = 1


class DiscoveryAnnouncementError(ValueError):
    """Raised when a native P2P discovery announcement is invalid."""


@dataclass(frozen=True)
class DiscoveryAnnouncement:
    """Validated public information advertised by a native P2P node."""

    node_id: str
    public_key: str
    host: str
    port: int
    timestamp: int
    protocol_version: int = DISCOVERY_PROTOCOL_VERSION


def _canonical_payload(fields: dict[str, Any]) -> bytes:
    return json.dumps(
        fields, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def create_announcement(
    identity_store: NodeIdentityStore,
    host: str,
    port: int,
    *,
    timestamp: int | None = None,
) -> bytes:
    """Create a signed, bounded announcement using the persistent node identity."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise DiscoveryAnnouncementError("Discovery host must be an IP address.") from exc
    # Port 0 explicitly means that this identity is discoverable but has no
    # currently advertised inbound P2P endpoint.
    if type(port) is not int or not 0 <= port <= 65535:
        raise DiscoveryAnnouncementError("Discovery port must be between 0 and 65535.")

    identity = identity_store.initialize()
    fields: dict[str, Any] = {
        "version": DISCOVERY_PROTOCOL_VERSION,
        "node_id": identity["node_id"],
        "public_key": identity["public_key"],
        "host": str(address),
        "port": int(port),
        "timestamp": int(time.time() if timestamp is None else timestamp),
    }
    signature = identity_store.sign(_canonical_payload(fields))
    message = dict(fields)
    message["signature"] = base64.b64encode(signature).decode("ascii")
    encoded = _canonical_payload(message)
    if len(encoded) > MAX_ANNOUNCEMENT_BYTES:
        raise DiscoveryAnnouncementError("Discovery announcement exceeds the size limit.")
    return encoded


def parse_announcement(
    payload: bytes,
    *,
    now: int | None = None,
    max_age_seconds: int = 60,
    future_tolerance_seconds: int = 10,
) -> DiscoveryAnnouncement:
    """Validate schema, timestamp, node ID, and Ed25519 signature of an announcement."""
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_ANNOUNCEMENT_BYTES:
        raise DiscoveryAnnouncementError("Discovery announcement size is invalid.")
    if max_age_seconds < 0 or future_tolerance_seconds < 0:
        raise ValueError("Timestamp tolerances must not be negative.")

    try:
        message = json.loads(payload.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DiscoveryAnnouncementError("Discovery announcement is not valid JSON.") from exc
    if not isinstance(message, dict):
        raise DiscoveryAnnouncementError("Discovery announcement must be a JSON object.")

    expected_keys = {
        "version", "node_id", "public_key", "host", "port", "timestamp", "signature"
    }
    if set(message) != expected_keys:
        raise DiscoveryAnnouncementError("Discovery announcement fields are invalid.")

    version = message["version"]
    node_id = message["node_id"]
    public_key = message["public_key"]
    host = message["host"]
    port = message["port"]
    timestamp = message["timestamp"]
    signature_text = message["signature"]

    if type(version) is not int or version != DISCOVERY_PROTOCOL_VERSION:
        raise DiscoveryAnnouncementError("Unsupported discovery protocol version.")
    if not isinstance(node_id, str) or len(node_id) != 71 or not node_id.startswith("sha256:"):
        raise DiscoveryAnnouncementError("Discovery node ID is invalid.")
    if not isinstance(public_key, str) or len(public_key) != 64:
        raise DiscoveryAnnouncementError("Discovery public key is invalid.")
    try:
        public_bytes = bytes.fromhex(public_key)
    except ValueError as exc:
        raise DiscoveryAnnouncementError("Discovery public key is not hexadecimal.") from exc
    expected_id = "sha256:" + hashlib.sha256(public_bytes).hexdigest()
    if node_id != expected_id:
        raise DiscoveryAnnouncementError("Node ID does not match the public key.")

    if not isinstance(host, str) or not host or len(host) > 64:
        raise DiscoveryAnnouncementError("Discovery host is invalid.")
    try:
        host = str(ipaddress.ip_address(host))
    except ValueError as exc:
        raise DiscoveryAnnouncementError("Discovery host must be an IP address.") from exc
    # Port 0 is an identity-only announcement, not a reachable endpoint.
    if type(port) is not int or not 0 <= port <= 65535:
        raise DiscoveryAnnouncementError("Discovery port is invalid.")
    if type(timestamp) is not int or timestamp < 0:
        raise DiscoveryAnnouncementError("Discovery timestamp is invalid.")
    current_time = int(time.time() if now is None else now)
    if timestamp < current_time - max_age_seconds:
        raise DiscoveryAnnouncementError("Discovery announcement has expired.")
    if timestamp > current_time + future_tolerance_seconds:
        raise DiscoveryAnnouncementError("Discovery announcement timestamp is in the future.")

    if not isinstance(signature_text, str):
        raise DiscoveryAnnouncementError("Discovery signature is invalid.")
    try:
        signature = base64.b64decode(signature_text, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise DiscoveryAnnouncementError("Discovery signature is not valid base64.") from exc

    unsigned_fields = {key: message[key] for key in expected_keys if key != "signature"}
    if not NodeIdentityStore.verify(public_key, _canonical_payload(unsigned_fields), signature):
        raise DiscoveryAnnouncementError("Discovery announcement signature is invalid.")

    return DiscoveryAnnouncement(
        node_id=node_id,
        public_key=public_key,
        host=host,
        port=port,
        timestamp=timestamp,
        protocol_version=version,
    )
