"""Small threaded TCP service for explicitly trusted Node Core OS P2P peers.

This service deliberately uses an explicit peer allowlist. It does not implement
global discovery, NAT traversal, or automatic trust-on-first-use.
"""
from __future__ import annotations

import socket
import threading
import uuid
from datetime import datetime, timezone
from collections.abc import Callable, Mapping
from typing import Any

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.session import (
    AuthenticatedPeerSession,
    PeerSessionError,
    receive_application_message,
    send_application_message,
)
from node_core.p2p.tls_transport import NodeTLSTransport, TLSTransportError


class PeerServiceError(RuntimeError):
    """Raised when the P2P service cannot start or connect safely."""


PeerHandler = Callable[[dict[str, str], Any], None]


class NodePeerService:
    """Threaded TCP listener/client for pinned TLS and authenticated P2P sessions."""

    def __init__(
        self,
        identity_store: NodeIdentityStore,
        tls_transport: NodeTLSTransport,
        trusted_peers: Mapping[str, bytes],
        host: str = "127.0.0.1",
        port: int = 0,
        timeout_seconds: float = 10.0,
        on_peer: PeerHandler | None = None,
    ) -> None:
        if not trusted_peers:
            raise ValueError("At least one explicitly trusted peer is required.")
        if not 0 <= port <= 65535:
            raise ValueError("port must be between 0 and 65535.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")
        for node_id, certificate in trusted_peers.items():
            if not isinstance(node_id, str) or not node_id.startswith("sha256:"):
                raise ValueError("Every trusted peer must have a sha256 node ID.")
            if not isinstance(certificate, bytes) or b"-----BEGIN CERTIFICATE-----" not in certificate:
                raise ValueError("Every trusted peer must have a PEM certificate.")
        self.identity_store = identity_store
        self.tls_transport = tls_transport
        self.trusted_peers = dict(trusted_peers)
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds
        self.on_peer = on_peer
        self._listener: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._workers: set[threading.Thread] = set()
        self._workers_lock = threading.Lock()
        self._trusted_peers_lock = threading.RLock()
        self._active_peers: dict[str, dict[str, str]] = {}
        self._active_peers_lock = threading.Lock()
        self._active_connections: set[socket.socket] = set()
        self._active_connections_lock = threading.Lock()
        self._connection_peers: dict[socket.socket, str] = {}
        self.last_error: str | None = None

    @property
    def address(self) -> tuple[str, int]:
        if self._listener is None:
            raise PeerServiceError("Peer service is not listening.")
        host, port = self._listener.getsockname()[:2]
        return str(host), int(port)

    @property
    def active_peers(self) -> list[dict[str, str]]:
        """Return a snapshot of currently authenticated inbound peer sessions."""
        with self._active_peers_lock:
            return [dict(peer) for peer in self._active_peers.values()]

    def _register_peer(self, peer: dict[str, str]) -> str:
        session_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        with self._active_peers_lock:
            self._active_peers[session_id] = {
                "session_id": session_id,
                "node_id": peer["node_id"],
                "connected_at": now,
                "last_seen": now,
            }
        return session_id

    def _touch_peer(self, session_id: str) -> None:
        with self._active_peers_lock:
            peer = self._active_peers.get(session_id)
            if peer is not None:
                peer["last_seen"] = datetime.now(timezone.utc).isoformat()

    def _active_peer_node_id(self, session_id: str) -> str | None:
        with self._active_peers_lock:
            peer = self._active_peers.get(session_id)
            return peer["node_id"] if peer else None

    def _unregister_peer(self, session_id: str | None) -> None:
        if session_id is None:
            return
        with self._active_peers_lock:
            self._active_peers.pop(session_id, None)

    def revoke_peer(self, node_id: str) -> int:
        """Remove one peer from the live allowlist and close only its inbound sessions."""
        with self._trusted_peers_lock:
            if node_id not in self.trusted_peers:
                return 0
            self.trusted_peers.pop(node_id, None)
            with self._active_connections_lock:
                connections = [
                    connection
                    for connection, peer_node_id in self._connection_peers.items()
                    if peer_node_id == node_id
                ]
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

    def start(self) -> tuple[str, int]:
        """Start listening; the port may be zero to request an OS-assigned port."""
        if self._listener is not None:
            return self.address
        self.tls_transport.ensure_certificate()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind((self.host, self.port))
            listener.listen(16)
            listener.settimeout(0.5)
        except OSError as exc:
            listener.close()
            raise PeerServiceError("Unable to bind P2P listener.") from exc
        self._listener = listener
        self._stop.clear()
        self._accept_thread = threading.Thread(
            target=self._accept_loop, name="node-core-p2p-accept", daemon=True
        )
        self._accept_thread.start()
        return self.address

    def stop(self) -> None:
        """Stop accepting new peers and wait briefly for worker threads."""
        self._stop.set()
        listener, self._listener = self._listener, None
        if listener is not None:
            try:
                listener.close()
            except OSError:
                pass
        # Revocation and shutdown must terminate established sessions as well
        # as the listening socket; otherwise an old allowlist could remain usable.
        with self._active_connections_lock:
            connections = list(self._active_connections)
        for active_connection in connections:
            try:
                active_connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                active_connection.close()
            except OSError:
                pass
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=self.timeout_seconds + 1)
            self._accept_thread = None
        with self._workers_lock:
            workers = list(self._workers)
        for worker in workers:
            worker.join(timeout=0.2)

    def connect(self, host: str, port: int, expected_peer_node_id: str) -> dict[str, str]:
        """Connect to one configured peer and complete TLS plus P2P authentication."""
        certificate = self.trusted_peers.get(expected_peer_node_id)
        if certificate is None:
            raise PeerServiceError("Target node is not in the explicit trusted-peer list.")
        raw_socket: socket.socket | None = None
        try:
            raw_socket = socket.create_connection((host, port), timeout=self.timeout_seconds)
            tls_socket = self.tls_transport.client_context([certificate]).wrap_socket(
                raw_socket, server_hostname=None
            )
            raw_socket = None
            with tls_socket:
                session = AuthenticatedPeerSession(
                    self.identity_store,
                    self.tls_transport,
                    expected_peer_node_id,
                    timeout_seconds=self.timeout_seconds,
                )
                peer = session.establish(tls_socket, "initiator")
                if self.on_peer:
                    self.on_peer(peer, tls_socket)
                return peer
        except (OSError, PeerSessionError, TLSTransportError) as exc:
            raise PeerServiceError("Unable to establish an authenticated P2P connection.") from exc
        finally:
            if raw_socket is not None:
                raw_socket.close()


    def request_status(
        self, host: str, port: int, expected_peer_node_id: str
    ) -> dict[str, str]:
        """Open an authenticated connection and return a validated remote STATUS response."""
        certificate = self.trusted_peers.get(expected_peer_node_id)
        if certificate is None:
            raise PeerServiceError("Target node is not in the explicit trusted-peer list.")
        raw_socket: socket.socket | None = None
        try:
            raw_socket = socket.create_connection(
                (host, port), timeout=self.timeout_seconds
            )
            tls_socket = self.tls_transport.client_context([certificate]).wrap_socket(
                raw_socket, server_hostname=None
            )
            raw_socket = None
            with tls_socket:
                session = AuthenticatedPeerSession(
                    self.identity_store,
                    self.tls_transport,
                    expected_peer_node_id,
                    timeout_seconds=self.timeout_seconds,
                )
                peer = session.establish(tls_socket, "initiator")
                request_id = uuid.uuid4().hex
                send_application_message(
                    tls_socket,
                    {
                        "version": 1,
                        "type": "STATUS",
                        "action": "request",
                        "request_id": request_id,
                    },
                )
                response = receive_application_message(tls_socket)
                if (
                    response.get("type") != "STATUS"
                    or response.get("action") != "response"
                    or response.get("request_id") != request_id
                ):
                    raise PeerServiceError("Peer returned an unexpected STATUS response.")
                return {
                    "node_id": peer["node_id"],
                    "state": response["state"],
                    "observed_at": response["observed_at"],
                    "request_id": request_id,
                }
        except (OSError, PeerSessionError, TLSTransportError, KeyError) as exc:
            raise PeerServiceError(
                "Unable to complete an authenticated STATUS request."
            ) from exc
        finally:
            if raw_socket is not None:
                raw_socket.close()

    def request_peers(
        self, host: str, port: int, expected_peer_node_id: str
    ) -> dict[str, Any]:
        """Request the remote node's known peer IDs without trusting them automatically."""
        certificate = self.trusted_peers.get(expected_peer_node_id)
        if certificate is None:
            raise PeerServiceError("Target node is not in the explicit trusted-peer list.")
        raw_socket: socket.socket | None = None
        try:
            raw_socket = socket.create_connection(
                (host, port), timeout=self.timeout_seconds
            )
            tls_socket = self.tls_transport.client_context([certificate]).wrap_socket(
                raw_socket, server_hostname=None
            )
            raw_socket = None
            with tls_socket:
                session = AuthenticatedPeerSession(
                    self.identity_store,
                    self.tls_transport,
                    expected_peer_node_id,
                    timeout_seconds=self.timeout_seconds,
                )
                peer = session.establish(tls_socket, "initiator")
                request_id = uuid.uuid4().hex
                send_application_message(
                    tls_socket,
                    {
                        "version": 1,
                        "type": "PEERS",
                        "action": "request",
                        "request_id": request_id,
                    },
                )
                response = receive_application_message(tls_socket)
                if (
                    response.get("type") != "PEERS"
                    or response.get("action") != "response"
                    or response.get("request_id") != request_id
                ):
                    raise PeerServiceError("Peer returned an unexpected PEERS response.")
                peer_ids = response["peers"]
                if peer["node_id"] in peer_ids:
                    raise PeerServiceError("Peer returned its own node ID in its PEERS list.")
                if self.identity_store.initialize()["node_id"] in peer_ids:
                    raise PeerServiceError("Peer returned this node's ID in its PEERS list.")
                return {
                    "node_id": peer["node_id"],
                    "request_id": request_id,
                    "peers": peer_ids,
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                    "trust_changed": False,
                }
        except (OSError, PeerSessionError, TLSTransportError, KeyError) as exc:
            raise PeerServiceError(
                "Unable to complete an authenticated PEERS request."
            ) from exc
        finally:
            if raw_socket is not None:
                raw_socket.close()

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            listener = self._listener
            if listener is None:
                break
            try:
                connection, _address = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                if not self._stop.is_set():
                    self.last_error = "P2P listener accept failed."
                break
            worker = threading.Thread(
                target=self._handle_connection,
                args=(connection,),
                name="node-core-p2p-peer",
                daemon=True,
            )
            with self._workers_lock:
                self._workers.add(worker)
            worker.start()

    def _handle_connection(self, connection: socket.socket) -> None:
        session_id: str | None = None
        tls_socket: socket.socket | None = None
        try:
            connection.settimeout(self.timeout_seconds)
            with self._trusted_peers_lock:
                trusted_certificates = list(self.trusted_peers.values())
            context = self.tls_transport.server_context(trusted_certificates)
            tls_socket = context.wrap_socket(connection, server_side=True)
            with self._active_connections_lock:
                self._active_connections.add(tls_socket)
            with tls_socket:
                certificate_peer = self.tls_transport.verify_peer_identity(tls_socket)
                node_id = certificate_peer["node_id"]
                session = AuthenticatedPeerSession(
                    self.identity_store,
                    self.tls_transport,
                    node_id,
                    timeout_seconds=self.timeout_seconds,
                )
                peer = session.establish(tls_socket, "responder")
                # Recheck and register under the same lock used by revoke_peer so
                # a handshake racing with revocation cannot create a stale session.
                with self._trusted_peers_lock:
                    if node_id not in self.trusted_peers:
                        raise PeerServiceError("Peer certificate is not in the trusted-peer list.")
                    session_id = self._register_peer(peer)
                    with self._active_connections_lock:
                        self._connection_peers[tls_socket] = node_id
                if self.on_peer:
                    self.on_peer(peer, tls_socket)
                self._serve_application_messages(tls_socket, session_id)
        except socket.timeout:
            # Idle peers may close without sending an application message.
            pass
        except (OSError, PeerSessionError, TLSTransportError, PeerServiceError) as exc:
            self.last_error = str(exc)
        finally:
            self._unregister_peer(session_id)
            if tls_socket is not None:
                with self._active_connections_lock:
                    self._active_connections.discard(tls_socket)
                    self._connection_peers.pop(tls_socket, None)
                try:
                    tls_socket.close()
                except OSError:
                    pass
            try:
                connection.close()
            except OSError:
                pass
            current = threading.current_thread()
            with self._workers_lock:
                self._workers.discard(current)

    def _serve_application_messages(
        self, tls_socket: socket.socket, session_id: str
    ) -> None:
        """Serve bounded application requests on an authenticated TLS connection."""
        while not self._stop.is_set():
            try:
                message = receive_application_message(tls_socket)
            except socket.timeout:
                return
            self._touch_peer(session_id)
            if message["type"] == "STATUS" and message["action"] == "request":
                send_application_message(
                    tls_socket,
                    {
                        "version": 1,
                        "type": "STATUS",
                        "action": "response",
                        "request_id": message["request_id"],
                        "state": "running",
                        "observed_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                continue
            if message["type"] == "PEERS" and message["action"] == "request":
                local_node_id = self.identity_store.initialize()["node_id"]
                peer_ids = sorted(
                    node_id
                    for node_id in self.trusted_peers
                    if node_id not in (local_node_id, self._active_peer_node_id(session_id))
                )[:100]
                send_application_message(
                    tls_socket,
                    {
                        "version": 1,
                        "type": "PEERS",
                        "action": "response",
                        "request_id": message["request_id"],
                        "peers": peer_ids,
                    },
                )
                continue
            send_application_message(
                tls_socket,
                {
                    "version": 1,
                    "type": "ERROR",
                    "code": "UNSUPPORTED_REQUEST",
                    "message": "This peer does not support that request.",
                },
            )
            return

    def __enter__(self) -> "NodePeerService":
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.stop()
