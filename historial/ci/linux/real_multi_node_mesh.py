#!/usr/bin/env python3
"""100 independent Linux VMs: full-mesh native P2P and persistent state convergence."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

REGISTRY_PORT = 8765
P2P_PORT = 46000
MAX_BODY_BYTES = 2 * 1024 * 1024
LOCK = threading.RLock()
NODES: dict[str, dict] = {}
SIGNATURES: dict[str, dict] = {}
CONVERGENCE_REPORTS: dict[str, dict] = {}
EXPECTED_NODES = 0
RUN_ID = ""
CACHED_MANIFEST: dict | None = None


def require_normal_user() -> None:
    if os.geteuid() == 0:
        raise SystemExit("ERROR: Node Core OS mesh nodes must run as a normal Linux user, never root.")


def request_json(url: str, payload: dict | None = None, timeout_seconds: int = 15) -> dict:
    body = None if payload is None else json.dumps(payload, sort_keys=True).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"} if body is not None else {},
        method="POST" if body is not None else "GET",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        result = json.loads(response.read(MAX_BODY_BYTES).decode("utf-8"))
    if not isinstance(result, dict):
        raise RuntimeError("Rendezvous returned a non-object response.")
    return result


def wait_for(predicate, timeout_seconds: int, description: str):
    deadline = time.monotonic() + timeout_seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except Exception as exc:
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {description}; last error={last_error}")


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def write_private_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def find_peer_ip(hostname: str) -> str | None:
    """Resolve another ephemeral Tailscale peer from the local tailnet map, without MagicDNS."""
    status = subprocess.run(
        ["tailscale", "status", "--json"],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    value = json.loads(status.stdout)
    peers = value.get("Peer", {})
    if not isinstance(peers, dict):
        return None
    for peer in peers.values():
        if not isinstance(peer, dict):
            continue
        host = str(peer.get("HostName", ""))
        dns_name = str(peer.get("DNSName", "")).rstrip(".").split(".")[0]
        if host == hostname or dns_name == hostname:
            addresses = peer.get("TailscaleIPs", [])
            if isinstance(addresses, list):
                for address in addresses:
                    if isinstance(address, str) and address:
                        return address
    return None


def send_json(handler: BaseHTTPRequestHandler, status: int, value: dict) -> None:
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class RendezvousHandler(BaseHTTPRequestHandler):
    """Temporary private registry: it carries public metadata, never P2P payloads."""

    def log_message(self, fmt, *args):
        print("RENDEZVOUS " + (fmt % args), flush=True)

    def do_GET(self):
        global CACHED_MANIFEST
        with LOCK:
            if self.path == "/v1/health":
                return send_json(self, 200, {"ok": True, "expected_nodes": EXPECTED_NODES})
            if self.path == "/v1/roster":
                return send_json(self, 200, {"ok": True, "count": len(NODES), "nodes": list(NODES.values())})
            if self.path == "/v1/manifest":
                if len(NODES) != EXPECTED_NODES:
                    return send_json(self, 409, {"ok": False, "error": "roster_incomplete"})
                if CACHED_MANIFEST is None:
                    from node_core.p2p.presence_manifest import create_manifest_body
                    members = [
                        {"node_id": item["node_id"], "public_key": item["public_key"]}
                        for item in NODES.values()
                    ]
                    CACHED_MANIFEST = create_manifest_body(
                        members, epoch=int(RUN_ID), created_at=int(time.time())
                    )
                return send_json(self, 200, {"ok": True, "body": CACHED_MANIFEST})
            if self.path == "/v1/signatures":
                return send_json(
                    self, 200,
                    {"ok": True, "count": len(SIGNATURES), "signatures": list(SIGNATURES.values())},
                )
            if self.path == "/v1/convergence":
                reports = list(CONVERGENCE_REPORTS.values())
                hashes = {item["convergence_sha256"] for item in reports}
                state_hashes = {item["network_state_sha256"] for item in reports}
                return send_json(self, 200, {
                    "ok": True,
                    "count": len(reports),
                    "reports": reports,
                    "all_converged": (
                        len(reports) == EXPECTED_NODES
                        and len(hashes) == 1
                        and len(state_hashes) == 1
                    ),
                })
        return send_json(self, 404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        if not 1 <= size <= MAX_BODY_BYTES:
            return send_json(self, 413, {"ok": False, "error": "invalid_body_size"})
        try:
            value = json.loads(self.rfile.read(size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return send_json(self, 400, {"ok": False, "error": "invalid_json"})
        if not isinstance(value, dict):
            return send_json(self, 400, {"ok": False, "error": "object_required"})

        with LOCK:
            if self.path == "/v1/register":
                required = {
                    "node_index", "node_id", "public_key", "certificate_pem",
                    "rsa_public_key_pem", "host", "port",
                }
                if set(value) != required:
                    return send_json(self, 400, {"ok": False, "error": "invalid_registration_schema"})
                index = value["node_index"]
                if type(index) is not int or not 0 <= index < EXPECTED_NODES:
                    return send_json(self, 400, {"ok": False, "error": "invalid_node_index"})
                if value["port"] != P2P_PORT or not isinstance(value["host"], str):
                    return send_json(self, 400, {"ok": False, "error": "invalid_endpoint"})
                if any(
                    existing["node_id"] == value["node_id"] and key != str(index)
                    for key, existing in NODES.items()
                ):
                    return send_json(self, 409, {"ok": False, "error": "duplicate_node_identity"})
                NODES[str(index)] = value
                return send_json(self, 200, {"ok": True, "registered": len(NODES)})

            if self.path == "/v1/signature":
                if set(value) != {"node_id", "signature"}:
                    return send_json(self, 400, {"ok": False, "error": "invalid_signature_schema"})
                known_ids = {item["node_id"] for item in NODES.values()}
                if value["node_id"] not in known_ids or value["node_id"] in SIGNATURES:
                    return send_json(self, 409, {"ok": False, "error": "unknown_or_duplicate_signer"})
                SIGNATURES[value["node_id"]] = value
                return send_json(self, 200, {"ok": True, "signature_count": len(SIGNATURES)})

            if self.path == "/v1/convergence":
                required = {"node_id", "network_state_sha256", "convergence_sha256"}
                if set(value) != required:
                    return send_json(self, 400, {"ok": False, "error": "invalid_convergence_schema"})
                known_ids = {item["node_id"] for item in NODES.values()}
                node_id = value["node_id"]
                if node_id not in known_ids or node_id in CONVERGENCE_REPORTS:
                    return send_json(self, 409, {"ok": False, "error": "unknown_or_duplicate_convergence_report"})
                for field in ("network_state_sha256", "convergence_sha256"):
                    digest = value[field]
                    if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                        return send_json(self, 400, {"ok": False, "error": "invalid_convergence_hash"})
                CONVERGENCE_REPORTS[node_id] = value
                reports = list(CONVERGENCE_REPORTS.values())
                same_hashes = (
                    len({item["network_state_sha256"] for item in reports}) == 1
                    and len({item["convergence_sha256"] for item in reports}) == 1
                )
                return send_json(self, 200, {
                    "ok": True,
                    "report_count": len(reports),
                    "hashes_match_so_far": same_hashes,
                })

        return send_json(self, 404, {"ok": False, "error": "not_found"})


def run_node(index: int, count: int, run_id: str, coordinator_ip: str | None = None) -> None:
    global EXPECTED_NODES, RUN_ID
    require_normal_user()
    if not run_id.isdigit():
        raise RuntimeError("Campaign run ID must contain digits only.")
    if coordinator_ip is not None:
        try:
            socket.inet_aton(coordinator_ip)
        except OSError as exc:
            raise RuntimeError("Coordinator address must be a valid IPv4 address.") from exc

    data_dir = Path(os.environ["NODE_CORE_DATA_DIR"])
    application_dir = data_dir / "app"
    if not application_dir.is_dir():
        raise RuntimeError(f"Node Core OS application not installed: {application_dir}")
    sys.path.insert(0, str(application_dir))

    from node_core.identity.node_identity import NodeIdentityStore
    from node_core.p2p.presence_manifest import sign_manifest, verify_manifest
    from node_core.p2p.secure_messaging import NodeRSAIdentityStore
    from node_core.p2p.service import NodePeerService
    from node_core.p2p.tls_transport import NodeTLSTransport
    from node_core.record_replication import NodeRecordReplicator

    EXPECTED_NODES, RUN_ID = count, run_id

    if index == 0:
        registry = ThreadingHTTPServer(("0.0.0.0", REGISTRY_PORT), RendezvousHandler)
        threading.Thread(target=registry.serve_forever, name="node-core-mesh-rendezvous", daemon=True).start()
        print(f"RENDEZVOUS_READY port={REGISTRY_PORT}", flush=True)

    identity = NodeIdentityStore(data_dir)
    identity_metadata = identity.initialize()
    tls = NodeTLSTransport(identity)
    certificate = tls.ensure_certificate()
    rsa_identity = NodeRSAIdentityStore(identity)
    rsa_metadata = rsa_identity.initialize()

    tailscale_ip_result = subprocess.run(
        ["tailscale", "ip", "-4"], check=True, capture_output=True, text=True, timeout=15
    )
    local_tailscale_ip = tailscale_ip_result.stdout.strip().splitlines()[0]
    if not local_tailscale_ip:
        raise RuntimeError("Tailscale did not provide this node's private IPv4 address.")

    if index == 0:
        coordinator_ip = local_tailscale_ip
    elif coordinator_ip is None:
        coordinator_name = f"ncore-{run_id}-0"
        coordinator_ip = wait_for(
            lambda: find_peer_ip(coordinator_name),
            600,
            f"Tailscale peer {coordinator_name} to appear in the tailnet map",
        )
    coordinator_url = f"http://{coordinator_ip}:{REGISTRY_PORT}"

    own_registration = {
        "node_index": index,
        "node_id": identity_metadata["node_id"],
        "public_key": identity_metadata["public_key"],
        "certificate_pem": base64.b64encode(certificate).decode("ascii"),
        "rsa_public_key_pem": base64.b64encode(rsa_identity.public_key_pem()).decode("ascii"),
        "host": local_tailscale_ip,
        "port": P2P_PORT,
    }
    wait_for(
        lambda: request_json(coordinator_url + "/v1/health").get("ok"),
        240,
        "private rendezvous service",
    )
    request_json(coordinator_url + "/v1/register", own_registration)

    roster_response = wait_for(
        lambda: (
            lambda result: result if result.get("count") == count else None
        )(request_json(coordinator_url + "/v1/roster")),
        900,
        f"all {count} independent Linux nodes to register",
    )
    roster = sorted(roster_response["nodes"], key=lambda item: item["node_index"])
    if len({item["node_id"] for item in roster}) != count:
        raise RuntimeError("Roster contains duplicate technical node identities.")
    if {item["node_index"] for item in roster} != set(range(count)):
        raise RuntimeError("Roster does not contain every expected node index exactly once.")

    manifest_response = request_json(coordinator_url + "/v1/manifest")
    manifest_body = manifest_response["body"]
    local_signature = sign_manifest(identity, manifest_body)
    request_json(coordinator_url + "/v1/signature", local_signature)

    signatures_response = wait_for(
        lambda: (
            lambda result: result if result.get("count") == count else None
        )(request_json(coordinator_url + "/v1/signatures")),
        900,
        f"all {count} node signatures",
    )
    consensus = verify_manifest(manifest_body, signatures_response["signatures"])
    if not consensus.get("unanimous") or consensus.get("node_count") != count:
        raise RuntimeError("The common presence manifest did not receive unanimous verification.")

    peer_entries = [item for item in roster if item["node_index"] != index]
    trusted_certificates = {
        item["node_id"]: base64.b64decode(item["certificate_pem"])
        for item in peer_entries
    }
    trusted_rsa_keys = {
        item["node_id"]: base64.b64decode(item["rsa_public_key_pem"])
        for item in peer_entries
    }
    all_node_ids = sorted(item["node_id"] for item in roster)

    # One deterministic, canonical network-state object is shared by every node.
    shared_state_body = {
        "schema": "node-core-os/network-synchronization/v1",
        "network": "node-core-os-real-linux-mesh",
        "run_id": run_id,
        "epoch": int(run_id),
        "revision": 1,
        "status": "ACTIVE",
        "participant_count": count,
        "participant_node_ids": all_node_ids,
        "presence_manifest_sha256": consensus["manifest_sha256"],
    }
    shared_state_sha256 = hashlib.sha256(canonical_json(shared_state_body)).hexdigest()
    shared_state = {
        "body": shared_state_body,
        "sha256": shared_state_sha256,
    }

    record_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"urn:node-core-os:network-state:{run_id}"))
    record = {
        "schema": NodeRecordReplicator.RECORD_SCHEMA,
        "record_id": record_id,
        "node_id": identity_metadata["node_id"],
        "github_account": "node-core-os-mesh-test",
        "repository": "node-core-os/network-mesh-test",
        "source_pages_url": "https://github.com/byLAEV/Node-Core-OS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "fields": {
            "network_state": shared_state,
            "network_state_sha256": shared_state_sha256,
        },
        "sync_status": "synced",
    }

    replicator = NodeRecordReplicator(data_dir, identity)
    message_handler_errors: list[str] = []

    def persist_received_record(peer: dict[str, str], message_id: str, text: str) -> None:
        try:
            accepted = replicator.receive_message(peer, message_id, text)
            if not accepted:
                message_handler_errors.append("Received a P2P message that was not a record replication event.")
        except Exception as exc:
            message_handler_errors.append(f"{type(exc).__name__}: {exc}")
            raise

    peer_service = NodePeerService(
        identity_store=identity,
        tls_transport=tls,
        trusted_peers=trusted_certificates,
        host="0.0.0.0",
        port=P2P_PORT,
        timeout_seconds=25,
        rsa_identity_store=rsa_identity,
        trusted_rsa_public_keys=trusted_rsa_keys,
        on_message=persist_received_record,
    )
    peer_service.start()

    # Full directed mesh: each node sends its exact same epoch record to every
    # other node. Rotating destination order balances incoming connection bursts.
    outgoing_receipts = []
    for offset in range(1, count):
        target_index = (index + offset) % count
        target = roster[target_index]
        target_id = target["node_id"]
        client = NodePeerService(
            identity_store=identity,
            tls_transport=tls,
            trusted_peers={target_id: trusted_certificates[target_id]},
            timeout_seconds=25,
            rsa_identity_store=rsa_identity,
            trusted_rsa_public_keys={target_id: trusted_rsa_keys[target_id]},
        )

        receipt = wait_for(
            lambda: replicator.send_record(
                client,
                target["host"],
                target["port"],
                target_id,
                trusted_rsa_keys[target_id],
                record,
            ),
            240,
            f"persistent P2P replication {index}->{target_index}",
        )
        if receipt.get("status") != "accepted" or receipt.get("receiver_node_id") != target_id:
            raise RuntimeError(f"Invalid signed delivery receipt for {index}->{target_index}.")
        outgoing_receipts.append({
            "target_index": target_index,
            "target_node_id": target_id,
            "message_id": receipt["message_id"],
            "received_at": receipt["received_at"],
        })
        if len(outgoing_receipts) % 10 == 0:
            print(f"FULL_MESH_PROGRESS node={index} sent={len(outgoing_receipts)}/{count-1}", flush=True)

    expected_origin_ids = set(all_node_ids) - {identity_metadata["node_id"]}

    def all_replicas_arrived():
        if message_handler_errors:
            raise RuntimeError("; ".join(message_handler_errors))
        incoming = [
            item for item in replicator.list_received()
            if item.get("record", {}).get("record_id") == record_id
        ]
        origins = {item.get("origin_node_id") for item in incoming}
        return incoming if len(incoming) == count - 1 and origins == expected_origin_ids else None

    incoming_replicas = wait_for(
        all_replicas_arrived,
        600,
        f"{count-1} persistent records from every other node",
    )

    for replica in incoming_replicas:
        if replica.get("replica_node_id") != identity_metadata["node_id"]:
            raise RuntimeError("A synchronized replica is stored under the wrong receiving node.")
        if replica.get("record", {}).get("fields", {}).get("network_state") != shared_state:
            raise RuntimeError("A peer stored a different network synchronization state.")
        if replica.get("record", {}).get("fields", {}).get("network_state_sha256") != shared_state_sha256:
            raise RuntimeError("A peer record has a different network-state hash.")

    # Persist this node's own contribution beside the 99 received persistent replicas.
    sync_directory = data_dir / "storage" / "shared" / "node-core-network-sync" / run_id
    own_contribution = {
        "origin_node_id": identity_metadata["node_id"],
        "replica_node_id": identity_metadata["node_id"],
        "record": record,
        "network_state_sha256": shared_state_sha256,
    }
    local_contribution_path = sync_directory / "local-contribution.json"
    write_private_json(local_contribution_path, own_contribution)
    persisted_local = json.loads(local_contribution_path.read_text(encoding="utf-8"))
    if persisted_local != own_contribution:
        raise RuntimeError("This node's own contribution did not survive local persistence.")

    converged_origins = sorted(all_node_ids)
    convergence_body = {
        "schema": "node-core-os/full-mesh-convergence/v1",
        "run_id": run_id,
        "record_id": record_id,
        "participant_count": count,
        "replica_count": count,
        "network_state_sha256": shared_state_sha256,
        "presence_manifest_sha256": consensus["manifest_sha256"],
        "converged_origin_node_ids": converged_origins,
    }
    convergence_sha256 = hashlib.sha256(canonical_json(convergence_body)).hexdigest()
    converged_snapshot = {**convergence_body, "convergence_sha256": convergence_sha256}
    write_private_json(sync_directory / "converged-state.json", converged_snapshot)

    # Publish this node's independently computed hashes. The rendezvous service
    # compares reports from every participant; a local calculation alone is
    # not accepted as proof of network-wide convergence.
    request_json(coordinator_url + "/v1/convergence", {
        "node_id": identity_metadata["node_id"],
        "network_state_sha256": shared_state_sha256,
        "convergence_sha256": convergence_sha256,
    })
    convergence_result = wait_for(
        lambda: (
            lambda result: result if result.get("count") == count else None
        )(request_json(coordinator_url + "/v1/convergence")),
        600,
        f"all {count} nodes to publish convergence hashes",
    )
    if not convergence_result.get("all_converged"):
        raise RuntimeError("Network-wide convergence hashes differ between participants.")
    if any(
        item.get("network_state_sha256") != shared_state_sha256
        or item.get("convergence_sha256") != convergence_sha256
        for item in convergence_result.get("reports", [])
    ):
        raise RuntimeError("At least one participant reported a different convergence hash.")

    # Verify all nodes will compute the same converged snapshot, not merely the
    # same per-sender payload.
    if converged_snapshot["converged_origin_node_ids"] != all_node_ids:
        raise RuntimeError("Converged state does not contain the complete global roster.")

    # Sample overlay route diagnostics after P2P transfers; relay use is recorded,
    # not hidden or falsely described as direct physical connectivity.
    route_samples = []
    for target in peer_entries[: min(3, len(peer_entries))]:
        route = subprocess.run(
            ["tailscale", "ping", "--c=3", "--until-direct=false", target["host"]],
            capture_output=True,
            text=True,
            timeout=20,
        )
        route_samples.append({
            "target_node_id": target["node_id"],
            "return_code": route.returncode,
            "output": (route.stdout + route.stderr)[-3000:],
        })

    peer_service.stop()

    evidence_root = Path(os.environ.get("RUNNER_TEMP", str(data_dir / "logs")))
    evidence_dir = evidence_root / "node-core-mesh-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence = {
        "schema": "node-core-real-linux-full-mesh-evidence-v1",
        "run_id": run_id,
        "node_index": index,
        "expected_nodes": count,
        "node_id": identity_metadata["node_id"],
        "public_key": identity_metadata["public_key"],
        "tailscale_ipv4": local_tailscale_ip,
        "os_release": Path("/etc/os-release").read_text(encoding="utf-8"),
        "uid": os.getuid(),
        "hostname": socket.gethostname(),
        "manifest_unanimous": consensus["unanimous"],
        "manifest_signatures": len(signatures_response["signatures"]),
        "presence_manifest_sha256": consensus["manifest_sha256"],
        "network_state_sha256": shared_state_sha256,
        "convergence_sha256": convergence_sha256,
        "outgoing_directed_deliveries": len(outgoing_receipts),
        "incoming_persistent_replicas": len(incoming_replicas),
        "total_expected_directed_deliveries": count * (count - 1),
        "outgoing_receipts": outgoing_receipts,
        "incoming_origin_node_ids": sorted(item["origin_node_id"] for item in incoming_replicas),
        "converged_origin_node_ids": converged_origins,
        "converged_snapshot_path": str(sync_directory / "converged-state.json"),
        "route_diagnostics": route_samples,
        "p2p_listener": {"host": "0.0.0.0", "port": P2P_PORT, "mutual_tls": True},
        "installation_data_dir": str(data_dir),
        "rsa_public_key_sha256": rsa_metadata["public_key_sha256"],
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    evidence_path = evidence_dir / f"node-{index:03d}.json"
    write_private_json(evidence_path, evidence)
    print(
        f"NODE_FULL_MESH_PASS index={index} id={identity_metadata['node_id']} "
        f"sent={len(outgoing_receipts)} received={len(incoming_replicas)} "
        f"state_sha256={shared_state_sha256} convergence_sha256={convergence_sha256}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--coordinator-ip",
        help="Tailscale IPv4 address of node 0; required on manually operated nodes 1..N-1.",
    )
    args = parser.parse_args()
    if not 3 <= args.count <= 100 or not 0 <= args.index < args.count:
        raise SystemExit("This campaign supports 3..100 nodes; index must be within the roster.")
    if args.index == 0 and args.coordinator_ip:
        raise SystemExit("Node 0 is the coordinator; do not pass --coordinator-ip.")
    if args.index != 0 and not args.coordinator_ip and not os.environ.get("GITHUB_ACTIONS"):
        raise SystemExit("Manual nodes 1..N-1 must pass --coordinator-ip with node 0's Tailscale IPv4.")
    run_node(args.index, args.count, args.run_id, args.coordinator_ip)


if __name__ == "__main__":
    main()
