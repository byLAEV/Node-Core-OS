"""Read-only restricted P2P identity/status sessions.

This transport is deliberately separate from NodePeerService and the application
message dispatcher. Callers must supply a certificate obtained from a validated,
signed discovery record; the certificate is an ephemeral TLS pin, not durable trust.
"""
from __future__ import annotations

import json
import re
import socket
import struct
import threading
import time
from collections import defaultdict
from typing import Callable

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.session import AuthenticatedPeerSession, PeerSessionError
from node_core.p2p.tls_transport import NodeTLSTransport, TLSTransportError


MAX_RESTRICTED_FRAME_BYTES = 1024
MAX_RESTRICTED_WORKERS = 8
MAX_REQUESTS_PER_SOURCE_PER_MINUTE = 12
REQUEST_ID_RE = re.compile(r"^[0-9a-f]{32}$")


class RestrictedSessionError(RuntimeError):
    """Raised when a restricted identity/status session is invalid."""


def _receive_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise RestrictedSessionError("Peer closed during restricted frame.")
        chunks.extend(chunk)
    return bytes(chunks)


def _pairs_without_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RestrictedSessionError("Duplicate JSON fields are forbidden.")
        result[key] = value
    return result


def _receive_restricted(sock: socket.socket) -> dict[str, object]:
    size = struct.unpack("!I", _receive_exact(sock, 4))[0]
    if size < 1 or size > MAX_RESTRICTED_FRAME_BYTES:
        raise RestrictedSessionError("Restricted frame size is invalid.")
    try:
        value = json.loads(
            _receive_exact(sock, size).decode("utf-8"),
            object_pairs_hook=_pairs_without_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RestrictedSessionError("Restricted frame is not valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise RestrictedSessionError("Restricted frame must be a JSON object.")
    return value


def _send_restricted(sock: socket.socket, message: dict[str, object]) -> None:
    payload = json.dumps(message, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    if not payload or len(payload) > MAX_RESTRICTED_FRAME_BYTES:
        raise RestrictedSessionError("Restricted response exceeds the frame limit.")
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def _validate_request(message: dict[str, object]) -> str:
    if set(message) != {"version", "type", "request_id"}:
        raise RestrictedSessionError("Restricted request fields are invalid.")
    if type(message["version"]) is not int or message["version"] != 1:
        raise RestrictedSessionError("Unsupported restricted protocol version.")
    if message["type"] != "IDENTITY_STATUS_REQUEST":
        raise RestrictedSessionError("Only IDENTITY_STATUS_REQUEST is permitted.")
    request_id = message["request_id"]
    if not isinstance(request_id, str) or not REQUEST_ID_RE.fullmatch(request_id):
        raise RestrictedSessionError("Restricted request ID is invalid.")
    return request_id


def _validate_response(message: dict[str, object], request_id: str) -> dict[str, object]:
    expected = {"version", "type", "request_id", "node_id", "protocol_version", "availability"}
    if set(message) != expected:
        raise RestrictedSessionError("Restricted response fields are invalid.")
    if type(message["version"]) is not int or message["version"] != 1:
        raise RestrictedSessionError("Unsupported restricted protocol version.")
    if message["type"] != "IDENTITY_STATUS_RESPONSE" or message["request_id"] != request_id:
        raise RestrictedSessionError("Restricted response does not match the request.")
    node_id = message["node_id"]
    if not isinstance(node_id, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", node_id):
        raise RestrictedSessionError("Restricted response node ID is invalid.")
    if type(message["protocol_version"]) is not int or message["protocol_version"] < 1:
        raise RestrictedSessionError("Restricted protocol version is invalid.")
    if message["availability"] not in {"available", "busy", "unavailable"}:
        raise RestrictedSessionError("Restricted availability is invalid.")
    return message


class RestrictedPeerSession:
    """One-shot, mutually authenticated, read-only identity/status session."""

    def __init__(
        self,
        identity_store: NodeIdentityStore,
        tls_transport: NodeTLSTransport,
        *,
        timeout_seconds: float = 5.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        self.identity_store = identity_store
        self.tls_transport = tls_transport
        self.timeout_seconds = timeout_seconds

    def request_status(
        self,
        host: str,
        port: int,
        expected_node_id: str,
        discovered_certificate_pem: bytes,
    ) -> dict[str, object]:
        """Connect using only the exact ephemeral certificate from signed discovery."""
        self.tls_transport.ensure_certificate()
        raw = socket.create_connection((host, port), timeout=self.timeout_seconds)
        try:
            with self.tls_transport.client_context([discovered_certificate_pem]).wrap_socket(
                raw, server_hostname=None
            ) as tls_socket:
                tls_socket.settimeout(self.timeout_seconds)
                peer = AuthenticatedPeerSession(
                    self.identity_store, self.tls_transport, expected_node_id,
                    timeout_seconds=self.timeout_seconds,
                ).establish(tls_socket, "initiator")
                request_id = __import__("uuid").uuid4().hex
                _send_restricted(tls_socket, {
                    "version": 1, "type": "IDENTITY_STATUS_REQUEST",
                    "request_id": request_id,
                })
                response = _validate_response(_receive_restricted(tls_socket), request_id)
                if response["node_id"] != peer["node_id"]:
                    raise RestrictedSessionError("TLS identity and restricted response differ.")
                return response
        except (OSError, PeerSessionError, TLSTransportError) as exc:
            raise RestrictedSessionError("Restricted peer authentication or request failed.") from exc
        finally:
            try:
                raw.close()
            except OSError:
                pass

    def serve_one(
        self,
        tls_socket: socket.socket,
        expected_peer_node_id: str,
        *,
        is_revoked: Callable[[str], bool],
        availability: str = "available",
    ) -> None:
        """Authenticate one discovered peer and serve only one status request."""
        if availability not in {"available", "busy", "unavailable"}:
            raise ValueError("availability is invalid.")
        tls_socket.settimeout(self.timeout_seconds)
        peer = AuthenticatedPeerSession(
            self.identity_store, self.tls_transport, expected_peer_node_id,
            timeout_seconds=self.timeout_seconds,
        ).establish(tls_socket, "responder")
        if is_revoked(peer["node_id"]):
            raise RestrictedSessionError("Peer identity is revoked.")
        request_id = _validate_request(_receive_restricted(tls_socket))
        if is_revoked(peer["node_id"]):
            raise RestrictedSessionError("Peer identity was revoked during the request.")
        local = self.identity_store.load()
        _send_restricted(tls_socket, {
            "version": 1,
            "type": "IDENTITY_STATUS_RESPONSE",
            "request_id": request_id,
            "node_id": local["node_id"],
            "protocol_version": 1,
            "availability": availability,
        })


class RestrictedSessionAdmission:
    """Bounded worker and per-source rate limiter for a restricted listener."""

    def __init__(
        self,
        *,
        max_workers: int = MAX_RESTRICTED_WORKERS,
        requests_per_minute: int = MAX_REQUESTS_PER_SOURCE_PER_MINUTE,
    ) -> None:
        if type(max_workers) is not int or not 1 <= max_workers <= MAX_RESTRICTED_WORKERS:
            raise ValueError("max_workers is outside the supported bound.")
        if type(requests_per_minute) is not int or not 1 <= requests_per_minute <= 60:
            raise ValueError("requests_per_minute is outside the supported bound.")
        self._slots = threading.BoundedSemaphore(max_workers)
        self._limit = requests_per_minute
        self._events: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def admit(self, source_ip: str, now: float | None = None) -> bool:
        instant = time.monotonic() if now is None else now
        with self._lock:
            recent = [stamp for stamp in self._events[source_ip] if instant - stamp < 60.0]
            if len(recent) >= self._limit:
                self._events[source_ip] = recent
                return False
            recent.append(instant)
            self._events[source_ip] = recent
            return True

    def acquire_worker(self) -> bool:
        return self._slots.acquire(blocking=False)

    def release_worker(self) -> None:
        self._slots.release()
