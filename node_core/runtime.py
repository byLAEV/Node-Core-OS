"""Runtime orchestration for Node Core OS."""
from pathlib import Path

from node_core.config import NodeConfig
from node_core.content import ContentManager
from node_core.evidence import EvidenceManager
from node_core.external_cids import ExternalCIDLibrary
from node_core.ipfs import KuboManager
from node_core.identity.node_identity import NodeIdentityStore
from node_core.identity.profile import IdentityProfileStore
from node_core.identity_presence import IdentityPresence
from node_core.my_life import MyLifeBlog
from node_core.network import NodeNetwork
from node_core.p2p.service import NodePeerService, PeerServiceError
from node_core.p2p.tls_transport import NodeTLSTransport
from node_core.p2p.trust_store import PeerTrustStore
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

        # Native P2P uses a separate technical identity and never requires Kubo.
        self.p2p_identity = NodeIdentityStore(self.config.data_dir)
        self.p2p_trust = PeerTrustStore(self.config.data_dir)
        self.p2p_tls = NodeTLSTransport(self.p2p_identity)
        self.p2p_service: NodePeerService | None = None
        self._booted = False

    @property
    def ipfs(self) -> KuboManager:
        return self.kubo

    def boot(self) -> None:
        self.config.ensure_directories()
        self.storage.initialize()
        self.config.save()
        self._booted = True

    def native_p2p_status(self) -> dict[str, object]:
        """Return local identity, trust, and listener state without requiring Kubo."""
        identity = self.p2p_identity.initialize()
        peers = self.p2p_trust.list_peers()
        service = self.p2p_service
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
            "last_error": service.last_error if service else None,
        }

    def start_native_p2p(self, host: str = "127.0.0.1", port: int = 0) -> tuple[str, int]:
        """Start the native P2P listener using the current persistent trust allowlist."""
        if self.p2p_service is not None:
            try:
                return self.p2p_service.address
            except PeerServiceError:
                self.p2p_service = None
        identity = self.p2p_identity.initialize()
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

    def stop_native_p2p(self) -> None:
        """Stop the native P2P listener if it is running."""
        service, self.p2p_service = self.p2p_service, None
        if service is not None:
            service.stop()

    def trust_peer_certificate(self, node_id: str, certificate_path: Path, label: str = "") -> dict[str, str]:
        """Trust a certificate explicitly after the operator verifies its fingerprint out of band."""
        certificate = Path(certificate_path).expanduser().read_bytes()
        return self.p2p_trust.add(node_id, certificate, label=label)

    def revoke_trusted_peer(self, node_id: str) -> dict[str, str]:
        """Persist peer revocation and stop the listener so its allowlist cannot stay stale."""
        result = self.p2p_trust.revoke(node_id)
        # The current service takes an immutable allowlist at construction. Stop it
        # after trust changes so a restart is required to load the updated allowlist.
        self.stop_native_p2p()
        return result

    def menu(self) -> None:
        if not self._booted:
            raise RuntimeError("Node Runtime must be booted before opening the menu.")
        try:
            MainMenu(self).run()
        finally:
            self.stop_native_p2p()
