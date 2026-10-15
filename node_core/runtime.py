"""Runtime orchestration for Node Core OS."""
from pathlib import Path
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

    def native_p2p_status(self) -> dict[str, object]:
        """Return local identity, trust, and listener state without requiring Kubo."""
        from node_core.p2p.service import PeerServiceError

        identity = self.p2p_identity.initialize()
        self.p2p_tls.ensure_certificate()
        peers = self.p2p_trust.list_peers()
        service = self.p2p_service
        discovery = self.p2p_discovery
        discovered_peers = list(discovery.snapshot()) if discovery is not None else []
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
            "last_error": service.last_error if service else None,
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
        }

    def start_native_discovery(self) -> bool:
        """Start signed LAN discovery without requiring Kubo or trusted peers."""
        if self.p2p_discovery is not None and self.p2p_discovery.running:
            return True
        try:
            from node_core.p2p.discovery_service import NodeDiscoveryService

            discovery = NodeDiscoveryService(
                self.p2p_identity,
                # Default endpoint advertised for native P2P; the listener remains
                # gated separately by the existing explicit trust store.
                p2p_port=45873,
            )
            discovery.start()
            self.p2p_discovery = discovery
            self._p2p_discovery_error = None
            return True
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            self.p2p_discovery = None
            self._p2p_discovery_error = str(exc)
            return False

    def stop_native_discovery(self) -> None:
        """Stop the LAN discovery worker if it is running."""
        discovery, self.p2p_discovery = self.p2p_discovery, None
        if discovery is not None:
            discovery.stop()

    def shutdown(self) -> None:
        """Stop all native P2P services owned by this runtime."""
        self.stop_native_p2p()
        self.stop_native_discovery()

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
        return result

    def menu(self) -> None:
        if not self._booted:
            raise RuntimeError("Node Runtime must be booted before opening the menu.")
        try:
            MainMenu(self).run()
        finally:
            self.stop_native_p2p()
