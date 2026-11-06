"""Read-only restricted P2P identity/status sessions.

This transport is deliberately separate from NodePeerService and the application
message dispatcher. Callers must supply a certificate obtained from a validated,
signed discovery record; the certificate is an ephemeral TLS pin, not durable trust.
"""
from __future__ import annotations

import json
import hashlib
import re
import selectors
import socket
import ssl
import struct
import threading
import time
from collections import defaultdict
from typing import Callable

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.session import AuthenticatedPeerSession, PeerSessionError
from node_core.p2p.tls_transport import NodeTLSTransport, TLSTransportError


MAX_RESTRICTED_FRAME_BYTES = 1024
MAX_RESTRICTED_WORKERS = 8
DEFAULT_RESTRICTED_TIMEOUT_SECONDS = 30.0
DEFAULT_TLS_HANDSHAKE_TIMEOUT_SECONDS = 60.0
MAX_REQUESTS_PER_SOURCE_PER_MINUTE = 12
REQUEST_ID_RE = re.compile(r"^[0-9a-f]{32}$")


class RestrictedSessionError(RuntimeError):
    """Raised when a restricted identity/status session is invalid."""


def _perform_tls_handshake(tls_socket: ssl.SSLSocket, timeout_seconds: float) -> None:
    """Complete TLS without blocking a worker past one absolute deadline.

    A non-blocking handshake lets shutdown interrupt clients that never send a
    ClientHello. The deadline is independent of socket idle timeouts used after
    the handshake, so slow but progressing connections receive a configurable
    window instead of an arbitrary short per-read timeout.
    """
    if timeout_seconds <= 0:
        raise ValueError("TLS handshake timeout must be positive.")
    deadline = time.monotonic() + timeout_seconds
    tls_socket.setblocking(False)
    while True:
        try:
            tls_socket.do_handshake()
            return
        except ssl.SSLWantReadError:
            event = selectors.EVENT_READ
        except ssl.SSLWantWriteError:
            event = selectors.EVENT_WRITE

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("TLS handshake exceeded its configured deadline.")
        with selectors.DefaultSelector() as selector:
            selector.register(tls_socket, event)
            ready = selector.select(remaining)
        if not ready:
            raise TimeoutError("TLS handshake exceeded its configured deadline.")


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
        timeout_seconds: float = DEFAULT_RESTRICTED_TIMEOUT_SECONDS,
        handshake_timeout_seconds: float = DEFAULT_TLS_HANDSHAKE_TIMEOUT_SECONDS,
    ) -> None:
        if timeout_seconds <= 0 or handshake_timeout_seconds <= 0:
            raise ValueError("Session timeouts must be positive.")
        self.identity_store = identity_store
        self.tls_transport = tls_transport
        self.timeout_seconds = timeout_seconds
        self.handshake_timeout_seconds = handshake_timeout_seconds

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
                raw, server_hostname=None, do_handshake_on_connect=False
            ) as tls_socket:
                _perform_tls_handshake(tls_socket, self.handshake_timeout_seconds)
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
        on_authenticated: Callable[[str], None] | None = None,
    ) -> str:
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
        if on_authenticated is not None:
            on_authenticated(peer["node_id"])
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
        return peer["node_id"]


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


class RestrictedPeerService:
    """Separate bounded listener for one-shot restricted identity/status requests."""

    def __init__(
        self,
        identity_store: NodeIdentityStore,
        tls_transport: NodeTLSTransport,
        certificate_candidates: Callable[[], dict[str, bytes]],
        *,
        is_revoked: Callable[[str], bool],
        host: str = "127.0.0.1",
        port: int = 0,
        timeout_seconds: float = DEFAULT_RESTRICTED_TIMEOUT_SECONDS,
        handshake_timeout_seconds: float = DEFAULT_TLS_HANDSHAKE_TIMEOUT_SECONDS,
        max_workers: int = MAX_RESTRICTED_WORKERS,
        requests_per_minute: int = MAX_REQUESTS_PER_SOURCE_PER_MINUTE,
    ) -> None:
        if (
            not 0 <= port <= 65535
            or timeout_seconds <= 0
            or handshake_timeout_seconds <= 0
        ):
            raise ValueError("Restricted listener address or timeout is invalid.")
        self.identity_store = identity_store
        self.tls_transport = tls_transport
        self.certificate_candidates = certificate_candidates
        self.is_revoked = is_revoked
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds
        self.handshake_timeout_seconds = handshake_timeout_seconds
        self.admission = RestrictedSessionAdmission(
            max_workers=max_workers, requests_per_minute=requests_per_minute
        )
        self._listener: socket.socket | None = None
        self._stop = threading.Event()
        self._accept_thread: threading.Thread | None = None
        self._workers: set[threading.Thread] = set()
        self._workers_lock = threading.Lock()
        # Track accepted sockets before TLS starts; stop() must also close
        # clients that have not authenticated yet.
        self._connections: set[socket.socket] = set()
        self._connections_lock = threading.RLock()
        self._active: dict[str, set[socket.socket]] = defaultdict(set)
        self._active_lock = threading.RLock()

    @property
    def address(self) -> tuple[str, int]:
        if self._listener is None:
            raise RestrictedSessionError("Restricted listener is not running.")
        host, port = self._listener.getsockname()[:2]
        return str(host), int(port)

    def start(self) -> tuple[str, int]:
        if self._listener is not None:
            return self.address
        self.tls_transport.ensure_certificate()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.host, self.port))
        listener.listen(MAX_RESTRICTED_WORKERS)
        listener.settimeout(0.5)
        self._listener = listener
        self._stop.clear()
        self._accept_thread = threading.Thread(
            target=self._accept_loop, name="node-core-p2p-restricted-accept", daemon=True
        )
        self._accept_thread.start()
        return self.address

    def _accept_loop(self) -> None:
        listener = self._listener
        while not self._stop.is_set() and listener is not None:
            try:
                raw, address = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            source_ip = str(address[0])
            if not self.admission.admit(source_ip) or not self.admission.acquire_worker():
                raw.close()
                continue
            with self._connections_lock:
                if self._stop.is_set():
                    raw.close()
                    self.admission.release_worker()
                    continue
                self._connections.add(raw)
            worker = threading.Thread(
                target=self._handle_connection, args=(raw,),
                name="node-core-p2p-restricted-worker", daemon=True,
            )
            with self._workers_lock:
                self._workers.add(worker)
            try:
                worker.start()
            except RuntimeError:
                with self._workers_lock:
                    self._workers.discard(worker)
                with self._connections_lock:
                    self._connections.discard(raw)
                raw.close()
                self.admission.release_worker()

    def _handle_connection(self, raw: socket.socket) -> None:
        tls_socket: socket.socket | None = None
        peer_node_id: str | None = None
        try:
            candidates = self.certificate_candidates()
            if not candidates or any(not isinstance(value, bytes) for value in candidates.values()):
                return
            tls_context = self.tls_transport.server_context(list(candidates.values()))
            # Swap the tracked raw socket for its TLS wrapper while holding the
            # same lock used by stop(), leaving no untracked shutdown window.
            with self._connections_lock:
                if self._stop.is_set():
                    return
                tls_socket = tls_context.wrap_socket(
                    raw, server_side=True, do_handshake_on_connect=False
                )
                self._connections.discard(raw)
                self._connections.add(tls_socket)
                raw = None
            _perform_tls_handshake(tls_socket, self.handshake_timeout_seconds)
            tls_socket.settimeout(self.timeout_seconds)
            peer = self.tls_transport.verify_peer_identity(tls_socket)
            peer_node_id = peer["node_id"]
            candidate_pem = candidates.get(peer_node_id)
            if candidate_pem is None:
                raise RestrictedSessionError("Peer certificate is not in the discovery candidate set.")
            candidate_der = x509.load_pem_x509_certificate(candidate_pem).public_bytes(
                serialization.Encoding.DER
            )
            presented_der = tls_socket.getpeercert(binary_form=True)
            if not presented_der or not __import__("hmac").compare_digest(
                hashlib.sha256(candidate_der).digest(),
                hashlib.sha256(presented_der).digest(),
            ):
                raise RestrictedSessionError("TLS peer certificate differs from its signed discovery candidate.")
            if self.is_revoked(peer_node_id):
                raise RestrictedSessionError("Peer is not currently eligible for restricted access.")

            def register(node_id: str) -> None:
                if self._stop.is_set():
                    raise RestrictedSessionError("Restricted peer service is stopping.")
                with self._active_lock:
                    if self._stop.is_set():
                        raise RestrictedSessionError("Restricted peer service is stopping.")
                    self._active[node_id].add(tls_socket)

            RestrictedPeerSession(
                self.identity_store, self.tls_transport,
                timeout_seconds=self.timeout_seconds,
            ).serve_one(
                tls_socket, peer_node_id, is_revoked=self.is_revoked,
                on_authenticated=register,
            )
        except (OSError, PeerSessionError, TLSTransportError, RestrictedSessionError):
            pass
        finally:
            if peer_node_id is not None and tls_socket is not None:
                with self._active_lock:
                    sessions = self._active.get(peer_node_id)
                    if sessions is not None:
                        sessions.discard(tls_socket)
                        if not sessions:
                            self._active.pop(peer_node_id, None)
            for connection in (tls_socket, raw):
                if connection is not None:
                    with self._connections_lock:
                        self._connections.discard(connection)
                    try:
                        connection.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    try:
                        connection.close()
                    except OSError:
                        pass
            self.admission.release_worker()
            with self._workers_lock:
                self._workers.discard(threading.current_thread())

    def revoke_peer(self, node_id: str) -> int:
        """Close all currently authenticated restricted sessions for a revoked node."""
        with self._active_lock:
            connections = list(self._active.pop(node_id, set()))
        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                connection.close()
            except OSError:
                pass
        return len(connections)

    def stop(self) -> None:
        self._stop.set()
        listener, self._listener = self._listener, None
        if listener is not None:
            try:
                listener.close()
            except OSError:
                pass
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=1.0)
        # Every accepted raw or TLS socket is tracked, including handshakes and
        # authentication in progress. Shutdown must not wait for peer input.
        with self._connections_lock:
            connections = list(self._connections)
            self._connections.clear()
        with self._active_lock:
            self._active.clear()
        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                connection.close()
            except OSError:
                pass
        with self._workers_lock:
            workers = list(self._workers)
        for worker in workers:
            worker.join(timeout=2.0)
        self._accept_thread = None
