"""Runtime orchestration for Node Core OS."""
from pathlib import Path
from datetime import datetime, timezone
import threading
from typing import Any

from node_core.config import NodeConfig
from node_core.content import ContentManager
from node_core.evidence import EvidenceManager
from node_core.external_cids import ExternalCIDLibrary
from node_core.ipfs import KuboManager
from node_core.identity.profile import IdentityProfileStore
from node_core.identity_presence import IdentityPresence
from node_core.my_life import MyLifeBlog
from node_core.network import NodeNetwork
from node_core.storage import StorageManager
from node_core.ui import MainMenu


class NodeRuntime:
    """Owns shared infrastructure and coordinates BIOS/Core interfaces."""

    def __init__(self) -> None:
        self.config = NodeConfig.load()
        self.storage = StorageManager(self.config.local_storage_path)
        self.kubo = KuboManager(
            executable=self.config.ipfs_executable,
            repo_path=self.config.ipfs_repo_path,
            api=self.config.ipfs_api,
            profile=self.config.ipfs_profile,
        )
        self.network = NodeNetwork(self.kubo)
        self.content = ContentManager(
            self.kubo,
            self.storage,
            gateway=self.config.ipfs_gateway,
        )
        self.evidence = EvidenceManager(self.content)
        self.identity_profile = IdentityProfileStore(self.config.data_dir)
        self.identity_presence = IdentityPresence(
            self.config.data_dir, self.identity_profile, self.network, self.kubo
        )
        self.external_cids = ExternalCIDLibrary(self.storage, self.kubo)
        self.my_life = MyLifeBlog(self.storage, self.content)

        # Keep the established CLI usable on installations that have not installed
        # the optional P2P cryptography dependency. Load P2P only on explicit use.
        self._p2p_identity: Any = None
        self._p2p_trust: Any = None
        self._p2p_tls: Any = None
        self.p2p_service: Any = None
        self.p2p_discovery: Any = None
        self._p2p_discovery_error: str | None = None
        self._p2p_discovery_retry_thread: threading.Thread | None = None
        self._p2p_discovery_stop_event = threading.Event()
        self._p2p_discovery_lock = threading.RLock()
        self._p2p_peer_monitor_thread: threading.Thread | None = None
        self._p2p_peer_monitor_stop_event = threading.Event()
        self._p2p_peer_monitor_lock = threading.RLock()
        self._p2p_peer_monitor_status: dict[str, dict[str, str]] = {}
        self._p2p_peer_monitor_error: str | None = None
        self._booted = False

    @property
    def ipfs(self) -> KuboManager:
        return self.kubo

    def _ensure_p2p_components(self) -> None:
        if self._p2p_identity is not None:
            return
        try:
            from node_core.identity.node_identity import NodeIdentityStore
            from node_core.p2p.tls_transport import NodeTLSTransport
            from node_core.p2p.trust_store import PeerTrustStore
        except ImportError as exc:
            raise RuntimeError(
                "Native P2P requires the 'cryptography' dependency. "
                "Install the project requirements before using Native P2P."
            ) from exc
        self._p2p_identity = NodeIdentityStore(self.config.data_dir)
        self._p2p_trust = PeerTrustStore(self.config.data_dir)
        self._p2p_tls = NodeTLSTransport(self._p2p_identity)

    @property
    def p2p_identity(self) -> Any:
        self._ensure_p2p_components()
        return self._p2p_identity

    @property
    def p2p_trust(self) -> Any:
        self._ensure_p2p_components()
        return self._p2p_trust

    @property
    def p2p_tls(self) -> Any:
        self._ensure_p2p_components()
        return self._p2p_tls

    def boot(self) -> None:
        self.config.ensure_directories()
        self.storage.initialize()
        self.config.save()
        self._booted = True
        # Discovery is independent of Kubo/IPFS and must not prevent the core
        # CLI from booting when multicast is unavailable on this network.
        self.start_native_discovery()
        # Start the authenticated listener automatically only when an explicit
        # trust allowlist already exists. The listener accepts no unknown identities.
        self._start_native_p2p_automation()

    def native_p2p_status(self) -> dict[str, object]:
        """Return local identity, trust, and listener state without requiring Kubo."""
        from node_core.p2p.service import PeerServiceError

        identity = self.p2p_identity.initialize()
        self.p2p_tls.ensure_certificate()
        peers = self.p2p_trust.list_peers()
        service = self.p2p_service
        discovery = self.p2p_discovery
        discovered_peers = list(discovery.snapshot()) if discovery is not None else []
        trust_by_node_id = {peer["node_id"]: peer["status"] for peer in peers}
        authenticated_inbound_node_ids = {
            peer["node_id"] for peer in (service.active_peers if service else [])
        }
        now = datetime.now(timezone.utc)
        outbound_peer_status = service.outbound_peers if service is not None else []
        recent_peer_status = {}
        for value in outbound_peer_status:
            if value.get("state") != "online":
                continue
            try:
                last_seen = datetime.fromisoformat(value["last_seen"])
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                if (now - last_seen).total_seconds() <= 20:
                    recent_peer_status[value["node_id"]] = {
                        **value,
                        "checked_at": value["last_seen"],
                        "state": "online",
                    }
            except (KeyError, TypeError, ValueError):
                continue
        discovered_peer_status = []
        for peer in discovered_peers:
            trust_status = trust_by_node_id.get(peer.node_id, "not_trusted")
            authenticated_inbound = peer.node_id in authenticated_inbound_node_ids
            # Entries in discovery.snapshot() have already passed the signed
            # announcement parser. This authenticates that announcement, not a
            # fresh interactive session and not authorization for application use.
            if trust_status == "revoked":
                state = "revoked"
            elif authenticated_inbound:
                state = "trusted_and_authenticated_inbound"
            elif trust_status == "trusted" and recent_peer_status.get(peer.node_id, {}).get("state") == "online":
                state = "trusted_and_recently_authenticated_outbound"
            elif trust_status == "trusted":
                state = "trusted_not_connected"
            else:
                state = "signed_announcement_verified_not_trusted"
            discovered_peer_status.append({
                "node_id": peer.node_id,
                "host": peer.host,
                "port": peer.port,
                "last_announcement": peer.timestamp,
                "announcement_signature_validated": True,
                "identity_authenticated": authenticated_inbound,
                "trust_status": trust_status,
                "authenticated_inbound_session": authenticated_inbound,
                "recent_outbound_check": recent_peer_status.get(peer.node_id),
                "state": state,
            })
        listening = False
        address: tuple[str, int] | None = None
        if service is not None:
            try:
                address = service.address
                listening = True
            except PeerServiceError:
                listening = False
        return {
            "node_id": identity["node_id"],
            "certificate_path": str(self.p2p_tls.certificate_path),
            "trusted_count": sum(peer["status"] == "trusted" for peer in peers),
            "revoked_count": sum(peer["status"] == "revoked" for peer in peers),
            "peers": peers,
            "service_running": listening,
            "listen_address": address,
            "active_peers": service.active_peers if service else [],
            "active_outbound_peers": outbound_peer_status,
            "recently_authenticated_peers": [value for value in recent_peer_status.values() if value.get("state") == "online"],
            "peer_monitor_running": bool(self._p2p_peer_monitor_thread and self._p2p_peer_monitor_thread.is_alive()),
            "peer_monitor_error": self._p2p_peer_monitor_error,
            "last_error": service.last_error if service else None,
            # The current built-in discovery service is LAN multicast only.
            # Keep WAN explicitly unavailable until a rendezvous/bootstrap service
            # is deployed and configured; never imply global discovery is active.
            "discovery_scope": "lan",
            "wan_discovery_running": False,
            "wan_discovery_error": "WAN discovery requires a configured rendezvous/bootstrap service.",
            "discovery_running": bool(discovery and discovery.running),
            "discovery_error": (discovery.last_error if discovery else None) or self._p2p_discovery_error,
            "discovered_peers": [
                {
                    "node_id": peer.node_id,
                    "host": peer.host,
                    "port": peer.port,
                    "last_announcement": peer.timestamp,
                }
                for peer in discovered_peers
            ],
            # Per-peer states deliberately separate discovery, trust, and live
            # authenticated inbound sessions. Discovery never grants trust.
            "discovered_peer_status": discovered_peer_status,
        }

    def _native_p2p_advertised_port(self) -> int:
        """Return a port only when a non-loopback native P2P listener is active."""
        service = self.p2p_service
        if service is None:
            return 0
        try:
            host, port = service.address
        except Exception:
            return 0
        if not isinstance(port, int) or not 1 <= port <= 65535:
            return 0
        # A listener bound only to loopback cannot be reached by other LAN nodes.
        if host.startswith("127.") or host == "::1" or host == "localhost":
            return 0
        return port

    def start_native_discovery(self) -> bool:
        """Start signed LAN discovery and schedule bounded retries after failures."""
        with self._p2p_discovery_lock:
            if self.p2p_discovery is not None and self.p2p_discovery.running:
                return True
            if self._try_start_native_discovery():
                return True
            retry = self._p2p_discovery_retry_thread
            if retry is None or not retry.is_alive():
                self._p2p_discovery_stop_event.clear()
                self._p2p_discovery_retry_thread = threading.Thread(
                    target=self._retry_native_discovery,
                    name="node-core-p2p-discovery-retry",
                    daemon=True,
                )
                self._p2p_discovery_retry_thread.start()
            return False

    def _try_start_native_discovery(self) -> bool:
        """Perform one discovery startup attempt and retain a useful error."""
        try:
            from node_core.p2p.discovery_service import NodeDiscoveryService

            discovery = NodeDiscoveryService(
                self.p2p_identity,
                # Identity announcements remain useful before a listener exists.
                # The service advertises port 0 until a reachable listener is active,
                # then reads its real bound port for each announcement.
                p2p_port=self._native_p2p_advertised_port,
            )
            discovery.start()
            self.p2p_discovery = discovery
            self._p2p_discovery_error = None
            return True
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            self.p2p_discovery = None
            self._p2p_discovery_error = str(exc)
            return False

    def _retry_native_discovery(self) -> None:
        """Retry discovery with bounded exponential backoff until shutdown."""
        delay_seconds = 1.0
        maximum_delay_seconds = 30.0
        while not self._p2p_discovery_stop_event.wait(delay_seconds):
            with self._p2p_discovery_lock:
                if self.p2p_discovery is not None and self.p2p_discovery.running:
                    return
                if self._try_start_native_discovery():
                    return
            delay_seconds = min(delay_seconds * 2.0, maximum_delay_seconds)

    def stop_native_discovery(self) -> None:
        """Stop LAN discovery and its retry worker."""
        self._p2p_discovery_stop_event.set()
        retry = self._p2p_discovery_retry_thread
        if retry is not None and retry is not threading.current_thread():
            retry.join(timeout=2.0)
        self._p2p_discovery_retry_thread = None
        with self._p2p_discovery_lock:
            discovery, self.p2p_discovery = self.p2p_discovery, None
            if discovery is not None:
                discovery.stop()

    def shutdown(self) -> None:
        """Stop all native P2P services owned by this runtime."""
        self.stop_native_peer_monitor()
        self.stop_native_p2p()
        self.stop_native_discovery()

    def _start_native_p2p_automation(self) -> None:
        """Start the allowlisted LAN listener and peer monitor when trust is configured."""
        try:
            if not self.p2p_trust.trusted_certificates():
                return
            if self.p2p_service is None:
                # Bind all local interfaces so other LAN nodes can reach this node.
                # NodePeerService still requires a trusted certificate and authenticated session.
                self.start_native_p2p(host="0.0.0.0", port=0)
            self.start_native_peer_monitor()
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            self._p2p_peer_monitor_error = str(exc)

    def start_native_peer_monitor(self) -> bool:
        """Periodically authenticate reachable, already-trusted LAN peers."""
        with self._p2p_peer_monitor_lock:
            if self._p2p_peer_monitor_thread is not None and self._p2p_peer_monitor_thread.is_alive():
                return True
            self._p2p_peer_monitor_stop_event.clear()
            self._p2p_peer_monitor_thread = threading.Thread(
                target=self._run_native_peer_monitor,
                name="node-core-p2p-peer-monitor",
                daemon=True,
            )
            self._p2p_peer_monitor_thread.start()
            return True

    def _run_native_peer_monitor(self) -> None:
        """Check discovered trusted peers with bounded timeouts and periodic retries."""
        interval_seconds = 5.0
        while not self._p2p_peer_monitor_stop_event.is_set():
            try:
                discovery = self.p2p_discovery
                discovered = list(discovery.snapshot()) if discovery is not None else []
                trusted = self.p2p_trust.trusted_certificates()
                if trusted and self.p2p_service is None:
                    self._start_native_p2p_automation()
                service = self.p2p_service
                if service is not None:
                    for peer in discovered:
                        if self._p2p_peer_monitor_stop_event.is_set():
                            break
                        if peer.node_id not in trusted or not peer.host or not 1 <= peer.port <= 65535:
                            continue
                        service.connect_persistent(peer.host, peer.port, peer.node_id)
                    with self._p2p_peer_monitor_lock:
                        self._p2p_peer_monitor_status = {
                            peer["node_id"]: dict(peer) for peer in service.outbound_peers
                        }
                self._p2p_peer_monitor_error = None
            except (ImportError, OSError, RuntimeError, ValueError) as exc:
                self._p2p_peer_monitor_error = str(exc)
            if self._p2p_peer_monitor_stop_event.wait(interval_seconds):
                break

    def stop_native_peer_monitor(self) -> None:
        """Stop automatic outbound checks cleanly."""
        self._p2p_peer_monitor_stop_event.set()
        thread = self._p2p_peer_monitor_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._p2p_peer_monitor_thread = None

    def start_native_p2p(self, host: str = "127.0.0.1", port: int = 0) -> tuple[str, int]:
        """Start the native P2P listener using the current persistent trust allowlist."""
        from node_core.p2p.service import NodePeerService, PeerServiceError

        if self.p2p_service is not None:
            try:
                return self.p2p_service.address
            except PeerServiceError:
                self.p2p_service = None
        self.p2p_identity.initialize()
        certificates = self.p2p_trust.trusted_certificates()
        if not certificates:
            raise PeerServiceError(
                "No trusted peers configured. Add and verify a peer certificate first."
            )
        self.p2p_tls.ensure_certificate()
        service = NodePeerService(
            identity_store=self.p2p_identity,
            tls_transport=self.p2p_tls,
            trusted_peers=certificates,
            host=host,
            port=port,
        )
        address = service.start()
        self.p2p_service = service
        return address

    def query_native_peer_status(
        self, host: str, port: int, node_id: str
    ) -> dict[str, str]:
        """Query one explicitly trusted native peer without requiring a local listener."""
        from node_core.p2p.service import NodePeerService, PeerServiceError

        certificates = self.p2p_trust.trusted_certificates()
        if node_id not in certificates:
            raise PeerServiceError("Target node is not in the explicit trusted-peer list.")
        client = NodePeerService(
            identity_store=self.p2p_identity,
            tls_transport=self.p2p_tls,
            trusted_peers=certificates,
            timeout_seconds=10.0,
        )
        return client.request_status(host, port, node_id)

    def query_native_peer_peers(
        self, host: str, port: int, node_id: str
    ) -> dict[str, object]:
        """Request a peer-ID list from one explicitly trusted node; never changes trust."""
        from node_core.p2p.service import NodePeerService, PeerServiceError

        certificates = self.p2p_trust.trusted_certificates()
        if node_id not in certificates:
            raise PeerServiceError("Target node is not in the explicit trusted-peer list.")
        client = NodePeerService(
            identity_store=self.p2p_identity,
            tls_transport=self.p2p_tls,
            trusted_peers=certificates,
            timeout_seconds=10.0,
        )
        return client.request_peers(host, port, node_id)

    def stop_native_p2p(self) -> None:
        """Stop the native P2P listener if it is running."""
        service, self.p2p_service = self.p2p_service, None
        if service is not None:
            service.stop()

    def trust_peer_certificate(self, node_id: str, certificate_path: Path, label: str = "") -> dict[str, str]:
        """Trust a certificate explicitly after the operator verifies its fingerprint out of band."""
        certificate = Path(certificate_path).expanduser().read_bytes()
        result = self.p2p_trust.add(node_id, certificate, label=label)
        # The running service has an immutable allowlist; stop it after trust
        # changes so it cannot continue using stale authorization.
        self.stop_native_p2p()
        # Rebuild the listener from the updated allowlist and resume automation.
        if self._booted:
            self._start_native_p2p_automation()
        return result

    def revoke_trusted_peer(self, node_id: str) -> dict[str, str]:
        """Persist revocation and close only this peer's sessions when the service is running."""
        result = self.p2p_trust.revoke(node_id)
        service = self.p2p_service
        if service is not None:
            if self.p2p_trust.trusted_certificates():
                service.revoke_peer(node_id)
            else:
                # A listener with an empty allowlist has no useful authenticated
                # sessions to serve, so stop it rather than leave it misleadingly active.
                self.stop_native_p2p()
        if self._booted and self.p2p_trust.trusted_certificates() and self.p2p_service is None:
            self._start_native_p2p_automation()
        elif not self.p2p_trust.trusted_certificates():
            self.stop_native_peer_monitor()
        return result

    def menu(self) -> None:
        if not self._booted:
            raise RuntimeError("Node Runtime must be booted before opening the menu.")
        try:
            MainMenu(self).run()
        finally:
            self.stop_native_peer_monitor()
            self.stop_native_p2p()
