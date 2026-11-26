"""Basic peer discovery and connectivity for Node Core OS."""

from dataclasses import dataclass
import json
import re
from typing import Any


@dataclass(frozen=True)
class NodeIdentity:
    peer_id: str
    addresses: tuple[str, ...]


@dataclass(frozen=True)
class NetworkStatus:
    identity: NodeIdentity
    connected_peers: tuple[str, ...]


class NodeNetwork:
    """Use the configured Kubo repository for safe, basic peer operations."""

    def __init__(self, kubo: Any) -> None:
        self.kubo = kubo

    def identity(self) -> NodeIdentity:
        result = self.kubo._run("id")
        try:
            payload = json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError("Kubo returned invalid identity JSON.") from exc

        peer_id = payload.get("ID")
        addresses = payload.get("Addresses", [])
        if not isinstance(peer_id, str) or not peer_id:
            raise RuntimeError("Kubo identity response did not include a peer ID.")
        if not isinstance(addresses, list):
            addresses = []
        return NodeIdentity(peer_id, tuple(str(item) for item in addresses))

    def connected_peers(self) -> tuple[str, ...]:
        result = self.kubo._run("swarm", "peers")
        peers = set()
        for line in result.stdout.splitlines():
            address = line.strip()
            match = re.search(r"/p2p/([^/]+)$", address)
            if match:
                peers.add(match.group(1))
        return tuple(sorted(peers))

    def status(self) -> NetworkStatus:
        return NetworkStatus(
            identity=self.identity(),
            connected_peers=self.connected_peers(),
        )

    def connect(self, multiaddr: str) -> str:
        address = multiaddr.strip()
        if not address or any(character.isspace() for character in address):
            raise ValueError("Enter a complete IPFS peer multiaddress.")
        if not address.startswith(("/ip4/", "/ip6/", "/dns/", "/dns4/", "/dns6/")):
            raise ValueError("Peer address must start with /ip4, /ip6, /dns, /dns4, or /dns6.")
        if not re.search(r"/tcp/[0-9]+/p2p/[A-Za-z0-9]+$", address):
            raise ValueError(
                "Peer address must end with /tcp/<port>/p2p/<peer-id>."
            )
        result = self.kubo._run("swarm", "connect", address)
        return result.stdout.strip() or "Kubo accepted the peer connection."

    def ping(self, peer_id: str) -> str:
        target = peer_id.strip()
        if not re.fullmatch(r"[A-Za-z0-9]{20,}", target):
            raise ValueError("Enter a valid IPFS peer ID.")
        result = self.kubo._run("ping", "-n", "1", target)
        return result.stdout.strip() or f"Ping completed for {target}."
