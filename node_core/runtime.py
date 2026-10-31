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
from node_core.network_diagnostics import collect_network_diagnostics
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
        self._p2p_rsa_identity: Any = None
        self._record_replicator: Any = None
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
        self._github_binding: Any = None
        self._booted = False
        self._kubo_start_error: str | None = None

    @property
    def ipfs(self) -> KuboManager:
        return self.kubo

    @property
    def github_binding(self) -> Any:
        """Load the optional GitHub binding only when an operator uses it."""
        if self._github_binding is None:
            from node_core.github_binding import GitHubNodeBinding
            from node_core.identity.node_identity import NodeIdentityStore

            identity = NodeIdentityStore(self.config.data_dir)
            self._github_binding = GitHubNodeBinding(self.config.data_dir, identity)
        return self._github_binding

    def _ensure_p2p_components(self) -> None:
        if self._p2p_identity is not None:
            return
        try:
            from node_core.identity.node_identity import NodeIdentityStore
            from node_core.p2p.tls_transport import NodeTLSTransport
            from node_core.p2p.trust_store import PeerTrustStore
            from node_core.p2p.secure_messaging import NodeRSAIdentityStore
            from node_core.record_replication import NodeRecordReplicator
        except ImportError as exc:
            raise RuntimeError(
                "Native P2P requires the 'cryptography' dependency. "
                "Install the project requirements before using Native P2P."
            ) from exc
        self._p2p_identity = NodeIdentityStore(self.config.data_dir)
        self._p2p_trust = PeerTrustStore(self.config.data_dir)
        self._p2p_tls = NodeTLSTransport(self._p2p_identity)
        self._p2p_rsa_identity = NodeRSAIdentityStore(self._p2p_identity)
        self._record_replicator = NodeRecordReplicator(self.config.data_dir, self._p2p_identity)

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
        # Start Kubo automatically with its initialized default bootstrap list.
        # This is outbound, non-root networking; it does not alter Android routes,
        # DNS, firewall rules, or native Node Core peer trust.
        if self.config.auto_start_kubo and self.kubo.is_installed():
            try:
                self.kubo.start()
                self._kubo_start_error = None
            except Exception as exc:
                self._kubo_start_error = str(exc)
        # Discovery is independent of Kubo/IPFS and must not prevent the core
        # CLI from booting when multicast is unavailable on this network.
        self.start_native_discovery()
        # Start the authenticated listener automatically only when an explicit
        # trust allowlist already exists. The listener accepts no unknown identities.
        self._start_native_p2p_automation()

    def refresh_network_status(self) -> dict[str, object]:
        """Retry local discovery and peer automation, then collect fresh network status.

        Worldwide native discovery is deliberately not marked active unless an actual
        rendezvous/bootstrap implementation is configured and running.
        """
        errors: list[str] = []
        try:
            if not self.start_native_discovery():
                detail = self._p2p_discovery_error or "LAN discovery could not start."
                errors.append(f"LAN discovery: {detail}")
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            errors.append(f"LAN discovery: {exc}")
        try:
            self._start_native_p2p_automation()
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            self._p2p_peer_monitor_error = str(exc)
            errors.append(f"Native P2P automation: {exc}")
        try:
            kubo_status = self.kubo.status()
            if (
                self.config.auto_start_kubo
                and kubo_status.installed
                and not kubo_status.running
            ):
                try:
                    self.kubo.start()
                    self._kubo_start_error = None
                    kubo_status = self.kubo.status()
                except Exception as start_exc:
                    self._kubo_start_error = str(start_exc)
                    errors.append(f"Kubo automatic startup: {start_exc}")
            elif self._kubo_start_error:
                errors.append(f"Kubo automatic startup: {self._kubo_start_error}")
        except Exception as exc:
            kubo_status = None
            errors.append(f"Kubo status: {exc}")
        kubo_peers: list[str] = []
        kubo_bootstrap: list[str] = []
        if kubo_status is not None and kubo_status.running:
            try:
                kubo_peers = list(self.network.connected_peers())
            except Exception as exc:
                errors.append(f"Kubo connected peers: {exc}")
            try:
                result = self.kubo._run("bootstrap", "list")
                kubo_bootstrap = [
                    line.strip()
                    for line in result.stdout.splitlines()
                    if line.strip()
                ]
            except Exception as exc:
                errors.append(f"Kubo bootstrap configuration: {exc}")
        else:
            errors.append("Kubo peer and bootstrap checks skipped because Kubo is not running.")
        try:
            network_diagnostics = collect_network_diagnostics()
        except Exception as exc:
            network_diagnostics = {"error": str(exc)}
            errors.append(f"System network diagnostics: {exc}")
        try:
            native_status = self.native_p2p_status()
        except Exception as exc:
            native_status = None
            errors.append(f"Native P2P status: {exc}")
        return {
            "kubo": kubo_status,
            "kubo_connected_peers": kubo_peers,
            "kubo_bootstrap_peers": kubo_bootstrap,
            "native_p2p": native_status,
            "network_diagnostics": network_diagnostics,
            "errors": errors,
        }

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
                state = "trusted_and_authenticated_outbound"
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
        """Maintain sessions to discovered trusted peers and retry with bounded intervals."""
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
        """Stop the automatic trusted-peer session manager cleanly."""
        self._p2p_peer_monitor_stop_event.set()
        thread = self._p2p_peer_monitor_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._p2p_peer_monitor_thread = None

    def _trusted_p2p_message_keys(self) -> dict[str, bytes]:
        """Load RSA message keys pinned for currently trusted peers."""
        import json
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        trusted = self.p2p_trust.trusted_certificates()
        path = self.config.data_dir / "p2p" / "trusted-message-keys.json"
        if not path.is_file():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError("Trusted P2P message-key file must be a JSON object.")
        result = {}
        for node_id, pem in data.items():
            if node_id not in trusted or not isinstance(pem, str):
                continue
            key = serialization.load_pem_public_key(pem.encode("ascii"))
            if not isinstance(key, rsa.RSAPublicKey) or key.key_size != 3072:
                raise RuntimeError("Pinned peer message keys must use RSA-3072.")
            result[node_id] = pem.encode("ascii")
        return result

    def trust_peer_message_key(self, node_id: str, public_key_pem: bytes) -> dict[str, str]:
        """Pin a peer RSA message key after verifying its fingerprint out of band."""
        import hashlib
        import json
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        if node_id not in self.p2p_trust.trusted_certificates():
            raise ValueError("Trust the peer Node Core certificate before pinning its message key.")
        key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(key, rsa.RSAPublicKey) or key.key_size != 3072:
            raise ValueError("Peer message public key must be RSA-3072.")
        path = self.config.data_dir / "p2p" / "trusted-message-keys.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        values = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        values[node_id] = public_key_pem.decode("ascii")
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(values, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
        temporary.replace(path)
        der = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        return {"node_id": node_id, "rsa_public_key_sha256": hashlib.sha256(der).hexdigest(), "status": "trusted"}

    def replicate_github_record(self, host: str, port: int, peer_node_id: str, record: dict[str, Any]) -> dict[str, Any]:
        """Send one locally owned GitHub Page record to an explicitly trusted peer."""
        from node_core.p2p.service import NodePeerService
        certificates = self.p2p_trust.trusted_certificates()
        if peer_node_id not in certificates:
            raise ValueError("Target node is not in the explicit trusted-peer list.")
        message_keys = self._trusted_p2p_message_keys()
        peer_key = message_keys.get(peer_node_id)
        if peer_key is None:
            raise ValueError("Pin the target node RSA message public key before replication.")
        client = NodePeerService(
            identity_store=self.p2p_identity, tls_transport=self.p2p_tls,
            trusted_peers=certificates, rsa_identity_store=self._p2p_rsa_identity,
            trusted_rsa_public_keys=message_keys, timeout_seconds=10.0,
        )
        return self._record_replicator.send_record(client, host, port, peer_node_id, peer_key, record)

    def replicate_synced_github_records(self, host: str, port: int, peer_node_id: str) -> dict[str, Any]:
        """Replicate all archived records already written to this operator GitHub repository."""
        receipts = []
        for record in self.github_binding.synced_records():
            receipt = self.replicate_github_record(host, port, peer_node_id, record)
            receipts.append({"record_id": record["record_id"], "status": receipt.get("status")})
        return {"peer_node_id": peer_node_id, "sent": len(receipts), "accepted": sum(x["status"] == "accepted" for x in receipts), "receipts": receipts}

    def received_github_record_replicas(self, origin_node_id: str | None = None) -> list[dict[str, Any]]:
        """List records replicated into this node shared local storage."""
        self.p2p_identity.initialize()
        return self._record_replicator.list_received(origin_node_id)

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
        self._p2p_rsa_identity.initialize()
        service = NodePeerService(
            identity_store=self.p2p_identity,
            tls_transport=self.p2p_tls,
            trusted_peers=certificates,
            host=host,
            port=port,
            rsa_identity_store=self._p2p_rsa_identity,
            trusted_rsa_public_keys=self._trusted_p2p_message_keys(),
            on_message=lambda peer, message_id, text: self._record_replicator.receive_message(peer, message_id, text),
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
