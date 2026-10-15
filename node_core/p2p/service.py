"""Small threaded TCP service for explicitly trusted Node Core OS P2P peers.

This service deliberately uses an explicit peer allowlist. It does not implement
global discovery, NAT traversal, or automatic trust-on-first-use.
"""
from __future__ import annotations

import socket
import threading
from collections.abc import Callable, Mapping
from typing import Any

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.session import AuthenticatedPeerSession, PeerSessionError
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
        self.last_error: str | None = None

    @property
    def address(self) -> tuple[str, int]:
        if self._listener is None:
            raise PeerServiceError("Peer service is not listening.")
        host, port = self._listener.getsockname()[:2]
        return str(host), int(port)

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
        try:
            connection.settimeout(self.timeout_seconds)
            context = self.tls_transport.server_context(self.trusted_peers.values())
            with context.wrap_socket(connection, server_side=True) as tls_socket:
                certificate_peer = self.tls_transport.verify_peer_identity(tls_socket)
                node_id = certificate_peer["node_id"]
                if node_id not in self.trusted_peers:
                    raise PeerServiceError("Peer certificate is not in the trusted-peer list.")
                session = AuthenticatedPeerSession(
                    self.identity_store,
                    self.tls_transport,
                    node_id,
                    timeout_seconds=self.timeout_seconds,
                )
                peer = session.establish(tls_socket, "responder")
                if self.on_peer:
                    self.on_peer(peer, tls_socket)
        except (OSError, PeerSessionError, TLSTransportError, PeerServiceError) as exc:
            self.last_error = str(exc)
        finally:
            try:
                connection.close()
            except OSError:
                pass
            current = threading.current_thread()
            with self._workers_lock:
                self._workers.discard(current)

    def __enter__(self) -> "NodePeerService":
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.stop()
