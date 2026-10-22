"""HTTPS rendezvous client for native Node Core OS P2P discovery.

The rendezvous service only distributes signed announcements. It never grants
peer trust; all actual sessions remain pinned, mutually authenticated TLS.
"""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from node_core.p2p.discovery import (
    MAX_ANNOUNCEMENT_BYTES,
    DiscoveryAnnouncement,
    DiscoveryAnnouncementError,
    parse_announcement,
)


class RendezvousError(RuntimeError):
    """Raised when a rendezvous endpoint or response is invalid."""


class NativeP2PRendezvousClient:
    """Small HTTPS-only client for publishing and retrieving signed announcements."""

    def __init__(
        self,
        endpoint: str,
        *,
        timeout_seconds: float = 8.0,
        max_response_bytes: int = 256 * 1024,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        parsed = urllib.parse.urlsplit(endpoint)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Rendezvous endpoint must be an HTTPS URL without embedded credentials.")
        if parsed.query or parsed.fragment:
            raise ValueError("Rendezvous endpoint must not contain a query or fragment.")
        if not 0 < timeout_seconds <= 60:
            raise ValueError("timeout_seconds must be between 0 and 60.")
        if not 1024 <= max_response_bytes <= 2 * 1024 * 1024:
            raise ValueError("max_response_bytes must be between 1024 and 2097152.")
        self.endpoint = endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes
        self.ssl_context = ssl_context or ssl.create_default_context()

    def health(self) -> dict[str, Any]:
        """Check that the configured rendezvous service is reachable and compatible."""
        result = self._request("GET", "/v1/health")
        if result.get("protocol") != "node-core-p2p-rendezvous-v1" or result.get("status") != "ok":
            raise RendezvousError("Rendezvous health response is incompatible.")
        return result

    def announce(self, signed_announcement: bytes) -> None:
        """Publish one existing signed announcement; never creates or trusts identities."""
        if not isinstance(signed_announcement, bytes) or not 1 <= len(signed_announcement) <= MAX_ANNOUNCEMENT_BYTES:
            raise ValueError("A bounded signed Node Core OS announcement is required.")
        # Validate locally before sending to an untrusted directory service.
        parse_announcement(signed_announcement)
        self._request(
            "POST",
            "/v1/announce",
            {"announcement": signed_announcement.decode("ascii")},
        )

    def peers(self, node_id: str) -> list[DiscoveryAnnouncement]:
        """Return validated signed announcements, excluding the local identity."""
        if not isinstance(node_id, str) or not node_id.startswith("sha256:") or len(node_id) != 71:
            raise ValueError("node_id must be a Node Core OS sha256 identity.")
        result = self._request("GET", "/v1/peers?node_id=" + urllib.parse.quote(node_id, safe=""))
        items = result.get("announcements")
        if not isinstance(items, list) or len(items) > 256:
            raise RendezvousError("Rendezvous peer list is malformed or exceeds its limit.")
        peers: list[DiscoveryAnnouncement] = []
        for item in items:
            if not isinstance(item, str):
                raise RendezvousError("Rendezvous peer announcement must be encoded text.")
            try:
                announcement = parse_announcement(item.encode("ascii"))
            except (UnicodeEncodeError, DiscoveryAnnouncementError) as exc:
                raise RendezvousError("Rendezvous returned an invalid signed announcement.") from exc
            if announcement.node_id != node_id and announcement.port != 0:
                peers.append(announcement)
        return peers

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint + path,
            data=body,
            method=method,
            headers={"Accept": "application/json", **({"Content-Type": "application/json"} if body is not None else {})},
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds, context=self.ssl_context
            ) as response:
                content_type = response.headers.get_content_type()
                if content_type != "application/json":
                    raise RendezvousError("Rendezvous response is not JSON.")
                data = response.read(self.max_response_bytes + 1)
                if len(data) > self.max_response_bytes:
                    raise RendezvousError("Rendezvous response exceeds the size limit.")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RendezvousError(f"Rendezvous request failed: {exc}") from exc
        try:
            decoded = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RendezvousError("Rendezvous returned invalid JSON.") from exc
        if not isinstance(decoded, dict) or decoded.get("ok") is not True:
            raise RendezvousError("Rendezvous returned an unsuccessful or malformed response.")
        return decoded
