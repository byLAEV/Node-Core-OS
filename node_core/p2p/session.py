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


PROTOCOL_VERSION = 1
MAX_PEER_LIST_ITEMS = 100


def validate_application_message(message: dict[str, Any]) -> dict[str, Any]:
    """Validate a versioned Node Core OS application message after authentication."""
    if not isinstance(message, dict):
        raise PeerSessionError("Application message must be a JSON object.")
    if message.get("version") != PROTOCOL_VERSION:
        raise PeerSessionError("Unsupported P2P application protocol version.")
    message_type = message.get("type")
    if not isinstance(message_type, str):
        raise PeerSessionError("Application message type is required.")
    if message_type == "STATUS":
        if message.get("action") not in ("request", "response"):
            raise PeerSessionError("STATUS action must be request or response.")
        request_id = message.get("request_id")
        if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
            raise PeerSessionError("STATUS request_id is invalid.")
        if message["action"] == "response":
            state = message.get("state")
            if state not in ("running", "degraded", "stopped", "unknown"):
                raise PeerSessionError("STATUS response state is invalid.")
            observed_at = message.get("observed_at")
            if not isinstance(observed_at, str) or not observed_at or len(observed_at) > 64:
                raise PeerSessionError("STATUS response observed_at is invalid.")
    elif message_type == "PEERS":
        peers = message.get("peers")
        if not isinstance(peers, list) or len(peers) > MAX_PEER_LIST_ITEMS:
            raise PeerSessionError("PEERS must contain at most 100 peer IDs.")
        for node_id in peers:
            if not isinstance(node_id, str) or not node_id.startswith("sha256:") or len(node_id) > 128:
                raise PeerSessionError("PEERS contains an invalid node ID.")
    elif message_type == "ERROR":
        code = message.get("code")
        detail = message.get("message")
        if not isinstance(code, str) or not code or len(code) > 64:
            raise PeerSessionError("ERROR code is invalid.")
        if not isinstance(detail, str) or len(detail) > 512:
            raise PeerSessionError("ERROR message is invalid.")
    else:
        raise PeerSessionError("Unknown P2P application message type.")
    return message


def send_application_message(sock: socket.socket, message: dict[str, Any]) -> None:
    """Send a validated, length-framed application message over an authenticated socket."""
    validate_application_message(message)
    _send_message(sock, message)


def receive_application_message(sock: socket.socket) -> dict[str, Any]:
    """Receive and validate a length-framed application message."""
    return validate_application_message(_receive_message(sock))


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
