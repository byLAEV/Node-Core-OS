#!/usr/bin/env python3
"""Real three-container, three-distribution native Node Core P2P test."""
from __future__ import annotations

import base64
import json
import os
import socket
import sys
import threading
import time
import uuid
from pathlib import Path


def require_user() -> None:
    if os.geteuid() == 0:
        raise SystemExit("P2P E2E must run as the normal nodecore user, never root or sudo.")


def load_application() -> None:
    app = Path(os.environ["NODE_CORE_DATA_DIR"]) / "app"
    sys.path.insert(0, str(app))


def paths() -> tuple[Path, Path]:
    data_dir = Path(os.environ["NODE_CORE_DATA_DIR"])
    shared = Path("/shared")
    shared.mkdir(parents=True, exist_ok=True)
    return data_dir, shared


def prepare(label: str) -> None:
    require_user()
    load_application()
    from node_core.identity.node_identity import NodeIdentityStore
    from node_core.p2p.secure_messaging import NodeRSAIdentityStore
    from node_core.p2p.tls_transport import NodeTLSTransport

    data_dir, shared = paths()
    identity = NodeIdentityStore(data_dir)
    metadata = identity.initialize()
    tls = NodeTLSTransport(identity)
    certificate = tls.ensure_certificate()
    rsa = NodeRSAIdentityStore(identity)
    rsa.initialize()
    info = {
        "label": label,
        "node_id": metadata["node_id"],
        "certificate_pem": base64.b64encode(certificate).decode("ascii"),
        "rsa_public_key_pem": base64.b64encode(rsa.public_key_pem()).decode("ascii"),
    }
    target = shared / f"{label}.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    print(f"PREPARED {label} {metadata['node_id']}")


def load_nodes(shared: Path) -> dict[str, dict[str, object]]:
    nodes = {}
    for label in ("a", "b", "c"):
        path = shared / f"{label}.json"
        if not path.is_file():
            raise RuntimeError(f"Missing node metadata: {path}")
        value = json.loads(path.read_text(encoding="utf-8"))
        value["certificate"] = base64.b64decode(value.pop("certificate_pem"))
        value["rsa_public_key"] = base64.b64decode(value.pop("rsa_public_key_pem"))
        nodes[label] = value
    if len({value["node_id"] for value in nodes.values()}) != 3:
        raise RuntimeError("The three Linux containers must have distinct Node IDs.")
    return nodes


def serve(label: str) -> None:
    require_user()
    load_application()
    from node_core.identity.node_identity import NodeIdentityStore
    from node_core.p2p.secure_messaging import NodeRSAIdentityStore
    from node_core.p2p.service import NodePeerService
    from node_core.p2p.tls_transport import NodeTLSTransport
    from node_core.record_replication import NodeRecordReplicator

    data_dir, shared = paths()
    nodes = load_nodes(shared)
    identity = NodeIdentityStore(data_dir)
    tls = NodeTLSTransport(identity)
    rsa = NodeRSAIdentityStore(identity)
    rsa.initialize()
    own_id = nodes[label]["node_id"]
    trusted = {
        value["node_id"]: value["certificate"]
        for name, value in nodes.items()
        if name != label
    }
    trusted_rsa = {
        value["node_id"]: value["rsa_public_key"]
        for name, value in nodes.items()
        if name != label
    }
    replicator = NodeRecordReplicator(data_dir, identity)
    service = NodePeerService(
        identity_store=identity,
        tls_transport=tls,
        trusted_peers=trusted,
        host="0.0.0.0",
        port=8765,
        timeout_seconds=10,
        rsa_identity_store=rsa,
        trusted_rsa_public_keys=trusted_rsa,
        on_message=lambda peer, message_id, text:
            replicator.receive_message(peer, message_id, text),
    )
    host, port = service.start()
    (shared / f"{label}.ready").write_text(
        json.dumps({"node_id": own_id, "host": host, "port": port}) + "\n",
        encoding="utf-8",
    )
    print(f"LISTENING {label} {host}:{port}", flush=True)
    try:
        threading.Event().wait()
    finally:
        service.stop()


def probe(label: str, target: str) -> None:
    require_user()
    host = target
    with socket.create_connection((host, 8765), timeout=3):
        print(f"TCP_OK {label} -> {target}")


def send(source: str, target: str) -> None:
    require_user()
    load_application()
    from node_core.identity.node_identity import NodeIdentityStore
    from node_core.p2p.secure_messaging import NodeRSAIdentityStore
    from node_core.p2p.service import NodePeerService
    from node_core.p2p.tls_transport import NodeTLSTransport
    from node_core.record_replication import NodeRecordReplicator

    data_dir, shared = paths()
    nodes = load_nodes(shared)
    identity = NodeIdentityStore(data_dir)
    tls = NodeTLSTransport(identity)
    rsa = NodeRSAIdentityStore(identity)
    rsa.initialize()
    sender = nodes[source]
    recipient = nodes[target]
    client = NodePeerService(
        identity_store=identity,
        tls_transport=tls,
        trusted_peers={recipient["node_id"]: recipient["certificate"]},
        timeout_seconds=10,
        rsa_identity_store=rsa,
        trusted_rsa_public_keys={
            recipient["node_id"]: recipient["rsa_public_key"]
        },
    )
    replicator = NodeRecordReplicator(data_dir, identity)
    record_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"node-core-cross-distro-{source}"))
    record = {
        "schema": NodeRecordReplicator.RECORD_SCHEMA,
        "record_id": record_id,
        "node_id": sender["node_id"],
        "github_account": f"operator-{source}",
        "repository": f"operator-{source}/node-core-client",
        "source_pages_url": f"https://operator-{source}.github.io/node-core-client/",
        "created_at_utc": "2026-10-31T00:00:00+00:00",
        "fields": {"message": f"synthetic record from {source} to {target}"},
        "sync_status": "synced",
    }
    for attempt in range(1, 4):
        try:
            first = replicator.send_record(
                client, target, 8765, recipient["node_id"],
                recipient["rsa_public_key"], record,
            )
            second = replicator.send_record(
                client, target, 8765, recipient["node_id"],
                recipient["rsa_public_key"], record,
            )
            if first.get("status") != "accepted" or second.get("status") != "accepted":
                raise RuntimeError(f"Unexpected P2P receipts: {first!r}, {second!r}")
            print(
                f"RECEIPTS_OK {source}->{target} record={record_id} "
                f"first={first['status']} duplicate={second['status']}"
            )
            return
        except (OSError, RuntimeError) as exc:
            if attempt == 3:
                raise
            print(f"Retry {attempt}: {exc}", file=sys.stderr)
            time.sleep(2)


def verify(target: str, source: str) -> None:
    require_user()
    load_application()
    from node_core.identity.node_identity import NodeIdentityStore
    from node_core.record_replication import NodeRecordReplicator

    data_dir, shared = paths()
    nodes = load_nodes(shared)
    identity = NodeIdentityStore(data_dir)
    replicator = NodeRecordReplicator(data_dir, identity)
    records = replicator.list_received(nodes[source]["node_id"])
    expected = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"node-core-cross-distro-{source}"))
    matches = [item for item in records if item["record"]["record_id"] == expected]
    if len(matches) != 1:
        raise AssertionError(
            f"{target} expected one persistent replica from {source}; found {len(matches)}"
        )
    item = matches[0]
    if item["replica_node_id"] != nodes[target]["node_id"]:
        raise AssertionError("Replica was not stored under the receiving node identity.")
    if item["record"]["fields"]["message"] != f"synthetic record from {source} to {target}":
        raise AssertionError("Persisted record contents differ from the sender.")
    print(f"PERSISTENCE_OK {source}->{target} record={expected} count=1")


def main() -> None:
    require_user()
    if len(sys.argv) < 2:
        raise SystemExit("Usage: three_node_native_p2p.py prepare|serve|probe|send|verify ...")
    command = sys.argv[1]
    if command == "prepare":
        prepare(sys.argv[2])
    elif command == "serve":
        serve(sys.argv[2])
    elif command == "probe":
        probe(sys.argv[2], sys.argv[3])
    elif command == "send":
        send(sys.argv[2], sys.argv[3])
    elif command == "verify":
        verify(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
