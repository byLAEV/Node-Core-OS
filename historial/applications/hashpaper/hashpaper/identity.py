"""Explicitly authorized access to Node Core OS identity and Peer ID."""

from __future__ import annotations

from typing import Any


class IdentityIntegrationError(RuntimeError):
    """Raised when the local identity or real technical node ID is unavailable."""


def load_identity_and_peer_id(runtime: Any) -> tuple[dict[str, Any], str]:
    """Load the saved identity and require a live Kubo Peer ID; never invent either."""
    profile = runtime.identity_profile.load()
    if profile is None:
        raise IdentityIntegrationError(
            "No local Node Core OS identity profile exists. Create one in Node Core BIOS > Identity Profile first."
        )
    status = runtime.kubo.status()
    if not status.running or not status.peer_id:
        raise IdentityIntegrationError(
            "A real Kubo Peer ID is unavailable. Start the Node Core OS Kubo service and retry."
        )
    return profile, status.peer_id


def associate_identity_with_peer(runtime: Any, profile: dict[str, Any], peer_id: str) -> dict[str, Any]:
    """Persist the user's explicitly authorized identity-to-node association."""
    current = profile.get("node_id")
    if current != peer_id:
        profile = runtime.identity_profile.associate_node(peer_id)
    return profile
