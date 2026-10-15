"""Automatic IPv4 multicast discovery for native Node Core OS P2P.

Discovery only finds and reports signed identities. It does not authorize peers or
create sessions; callers must use the existing authenticated peer service.
"""
from __future__ import annotations

from dataclasses import replace
import ipaddress
import socket
import threading
import time
from collections.abc import Callable

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.discovery import (
    MAX_ANNOUNCEMENT_BYTES,
    DiscoveryAnnouncement,
    DiscoveryAnnouncementError,
    create_announcement,
    parse_announcement,
)


DEFAULT_MULTICAST_GROUP = "239.255.42.99"
DEFAULT_MULTICAST_PORT = 45872
DEFAULT_ANNOUNCE_INTERVAL_SECONDS = 15.0
DEFAULT_PEER_TTL_SECONDS = 60.0
MAX_DISCOVERED_PEERS = 256


class DiscoveryServiceError(RuntimeError):
    """Raised when LAN discovery cannot be initialized safely."""


class NodeDiscoveryService:
    """Threaded IPv4 multicast announcer and signed peer registry."""

    def __init__(
        self,
        identity_store: NodeIdentityStore,
        *,
        p2p_port: int,
        multicast_group: str = DEFAULT_MULTICAST_GROUP,
        multicast_port: int = DEFAULT_MULTICAST_PORT,
        announce_interval_seconds: float = DEFAULT_ANNOUNCE_INTERVAL_SECONDS,
        peer_ttl_seconds: float = DEFAULT_PEER_TTL_SECONDS,
        interface_ip: str | None = None,
        on_peer: Callable[[DiscoveryAnnouncement], None] | None = None,
    ) -> None:
        if not 1 <= p2p_port <= 65535:
            raise ValueError("p2p_port must be between 1 and 65535.")
        try:
            group = ipaddress.ip_address(multicast_group)
            interface = ipaddress.ip_address(interface_ip) if interface_ip else None
        except ValueError as exc:
            raise ValueError("Multicast group and interface must be IP addresses.") from exc
        if group.version != 4 or not group.is_multicast:
            raise ValueError("multicast_group must be an IPv4 multicast address.")
        if interface is not None and interface.version != 4:
            raise ValueError("interface_ip must be an IPv4 address.")
        if not 1 <= multicast_port <= 65535:
            raise ValueError("multicast_port must be between 1 and 65535.")
        if announce_interval_seconds <= 0 or peer_ttl_seconds <= 0:
            raise ValueError("Discovery intervals must be positive.")

        self.identity_store = identity_store
        self.p2p_port = p2p_port
        self.multicast_group = str(group)
        self.multicast_port = multicast_port
        self.announce_interval_seconds = announce_interval_seconds
        self.peer_ttl_seconds = peer_ttl_seconds
        self.interface_ip = str(interface) if interface else None
        self.on_peer = on_peer
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._peers: dict[str, tuple[DiscoveryAnnouncement, float]] = {}
        self._last_error: str | None = None
        self._node_id: str | None = None
        self._bound_interface: str | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def last_error(self) -> str | None:
        with self._lock:
            return self._last_error

    def start(self) -> None:
        """Start multicast reception and periodic signed announcements."""
        if self.running:
            return
        identity = self.identity_store.initialize()
        interface_ip = self.interface_ip or self._default_interface_ip()
        if interface_ip == "0.0.0.0" or interface_ip.startswith("127."):
            raise DiscoveryServiceError(
                "No usable LAN interface was found for multicast discovery."
            )

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", self.multicast_port))
            membership = socket.inet_aton(self.multicast_group) + socket.inet_aton(interface_ip)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface_ip))
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
            sock.settimeout(0.5)
        except OSError as exc:
            sock.close()
            raise DiscoveryServiceError(f"Cannot initialize LAN discovery: {exc}") from exc

        self._node_id = identity["node_id"]
        self._bound_interface = interface_ip
        self._socket = sock
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="node-core-p2p-discovery",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout_seconds: float = 3.0) -> None:
        """Stop discovery and release its UDP socket."""
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(0.0, timeout_seconds))
        sock = self._socket
        self._socket = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        self._thread = None
        self._bound_interface = None

    def snapshot(self) -> tuple[DiscoveryAnnouncement, ...]:
        """Return non-expired peers, oldest entries first, without granting trust."""
        cutoff = time.monotonic() - self.peer_ttl_seconds
        with self._lock:
            expired = [
                node_id for node_id, (_, seen_at) in self._peers.items()
                if seen_at < cutoff
            ]
            for node_id in expired:
                self._peers.pop(node_id, None)
            return tuple(peer for peer, _ in sorted(
                self._peers.values(), key=lambda item: item[1]
            ))

    def _default_interface_ip(self) -> str:
        """Select the routed local IPv4 address without sending application data."""
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect((self.multicast_group, self.multicast_port))
            return str(probe.getsockname()[0])
        except OSError as exc:
            raise DiscoveryServiceError(
                "Cannot determine a local IPv4 interface for discovery."
            ) from exc
        finally:
            probe.close()

    def _run(self) -> None:
        next_announcement = 0.0
        sock = self._socket
        if sock is None or self._bound_interface is None:
            return
        destination = (self.multicast_group, self.multicast_port)

        while not self._stop_event.is_set():
            now = time.monotonic()
            if now >= next_announcement:
                try:
                    payload = create_announcement(
                        self.identity_store,
                        self._bound_interface,
                        self.p2p_port,
                    )
                    if len(payload) <= MAX_ANNOUNCEMENT_BYTES:
                        sock.sendto(payload, destination)
                    next_announcement = now + self.announce_interval_seconds
                except (OSError, DiscoveryAnnouncementError, RuntimeError) as exc:
                    with self._lock:
                        self._last_error = str(exc)
                    next_announcement = now + self.announce_interval_seconds

            try:
                payload, sender = sock.recvfrom(MAX_ANNOUNCEMENT_BYTES + 1)
            except socket.timeout:
                continue
            except OSError as exc:
                if not self._stop_event.is_set():
                    with self._lock:
                        self._last_error = str(exc)
                break

            if self._stop_event.is_set():
                continue
            try:
                announcement = parse_announcement(payload)
            except (DiscoveryAnnouncementError, ValueError):
                continue
            if announcement.node_id == self._node_id:
                continue

            # The observed source IP is used for LAN routing; never trust a
            # different address merely because the sender signed that claim.
            peer = replace(announcement, host=sender[0])
            discovered_at = time.monotonic()
            with self._lock:
                self._peers[peer.node_id] = (peer, discovered_at)
                while len(self._peers) > MAX_DISCOVERED_PEERS:
                    oldest_id = min(self._peers, key=lambda key: self._peers[key][1])
                    self._peers.pop(oldest_id, None)
                self._last_error = None
            if self.on_peer is not None:
                try:
                    self.on_peer(peer)
                except Exception:
                    # A UI or observer callback must not stop discovery.
                    pass
