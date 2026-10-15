"""Length-framed, mutually authenticated Node Core OS P2P sessions over TLS sockets."""
from __future__ import annotations

import json
import socket
import struct
from typing import Any

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.authentication import PeerAuthenticationError, PeerAuthenticator
from node_core.p2p.tls_transport import NodeTLSTransport, TLSTransportError


class PeerSessionError(RuntimeError):
    """Raised when a peer session cannot be safely established or used."""


MAX_MESSAGE_BYTES = 64 * 1024
DEFAULT_TIMEOUT_SECONDS = 10.0


def _receive_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise PeerSessionError("Peer closed the connection during a message.")
        chunks.extend(chunk)
    return bytes(chunks)


def _send_message(sock: socket.socket, message: dict[str, Any]) -> None:
    try:
        payload = json.dumps(
            message, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PeerSessionError("Message is not JSON serializable.") from exc
    if not payload or len(payload) > MAX_MESSAGE_BYTES:
        raise PeerSessionError("Message exceeds the permitted size.")
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def _receive_message(sock: socket.socket) -> dict[str, Any]:
    size = struct.unpack("!I", _receive_exact(sock, 4))[0]
    if size < 1 or size > MAX_MESSAGE_BYTES:
        raise PeerSessionError("Peer message length is invalid or too large.")
    try:
        message = json.loads(_receive_exact(sock, size).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PeerSessionError("Peer message is not valid UTF-8 JSON.") from exc
    if not isinstance(message, dict):
        raise PeerSessionError("Peer message must be a JSON object.")
    return message


class AuthenticatedPeerSession:
    """Perform Node Core OS HELLO/AUTH on an already-established pinned TLS socket.

    Callers are responsible for creating the TLS socket with NodeTLSTransport,
    supplying the expected node ID, and closing the socket after use.
    """

    def __init__(
        self,
        identity_store: NodeIdentityStore,
        tls_transport: NodeTLSTransport,
        expected_peer_node_id: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not isinstance(expected_peer_node_id, str) or not expected_peer_node_id.startswith("sha256:"):
            raise ValueError("An expected sha256 node ID is required.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")
        self.identity_store = identity_store
        self.tls_transport = tls_transport
        self.expected_peer_node_id = expected_peer_node_id
        self.timeout_seconds = timeout_seconds

    def establish(self, tls_socket: socket.socket, role: str) -> dict[str, str]:
        """Authenticate both identities over TLS and return the verified peer."""
        if role not in ("initiator", "responder"):
            raise ValueError("role must be 'initiator' or 'responder'.")
        tls_socket.settimeout(self.timeout_seconds)
        try:
            tls_peer = self.tls_transport.verify_peer_identity(
                tls_socket, self.expected_peer_node_id
            )
            local_hello = PeerAuthenticator.create_hello(self.identity_store)
            if role == "initiator":
                _send_message(tls_socket, local_hello)
                remote_hello = _receive_message(tls_socket)
            else:
                remote_hello = _receive_message(tls_socket)
                _send_message(tls_socket, local_hello)

            if remote_hello.get("node_id") != tls_peer["node_id"]:
                raise PeerSessionError("TLS certificate identity differs from P2P HELLO.")
            if remote_hello.get("node_id") != self.expected_peer_node_id:
                raise PeerSessionError("P2P HELLO does not match the expected peer.")

            local_auth = PeerAuthenticator.create_auth(
                self.identity_store, local_hello, remote_hello, role
            )
            if role == "initiator":
                _send_message(tls_socket, local_auth)
                remote_auth = _receive_message(tls_socket)
                PeerAuthenticator.verify_auth(
                    remote_auth, remote_hello, local_hello, role
                )
            else:
                remote_auth = _receive_message(tls_socket)
                PeerAuthenticator.verify_auth(
                    remote_auth, remote_hello, local_hello, role
                )
                _send_message(tls_socket, local_auth)

            return {
                "node_id": remote_hello["node_id"],
                "public_key": remote_hello["public_key"],
                "authentication": "tls1.3+ed25519_mutual_challenge_response",
            }
        except (OSError, PeerAuthenticationError, TLSTransportError, KeyError, AttributeError) as exc:
            if isinstance(exc, PeerSessionError):
                raise
            raise PeerSessionError("Mutual P2P session authentication failed.") from exc
        except PeerSessionError:
            raise
