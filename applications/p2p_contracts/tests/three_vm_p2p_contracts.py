#!/usr/bin/env python3
"""Cross-VM Node Core P2P Contracts acceptance test using three real Kubo daemons.

Each invocation runs on its own Ubuntu GitHub-hosted runner as an ordinary user.
Only synthetic test data is used. The Kubo HTTP API remains bound to localhost;
the workflow exposes only the libp2p swarm TCP port through a temporary TCP tunnel.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

if os.getuid() == 0:
    raise SystemExit("ERROR: this test must run as a normal user, never root.")

APP_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(APP_ROOT))

from node_core.runtime import NodeRuntime
from applications.p2p_contracts.p2p_contracts.service import P2PContractsService
from applications.p2p_contracts.p2p_contracts.propagation import (
    PropagationProtocol,
)
import applications.p2p_contracts.p2p_contracts.propagation as propagation_module


def wait_until(description, predicate, timeout=60.0, interval=0.25):
    deadline = time.monotonic() + timeout
    last_value = None
    while time.monotonic() < deadline:
        last_value = predicate()
        if last_value:
            return last_value
        time.sleep(interval)
    raise AssertionError(f"Timed out waiting for {description}; last value={last_value!r}")


def load_peer_endpoints(path: Path, local_role: str) -> list[dict]:
    records = json.loads(path.read_text(encoding="utf-8"))
    expected = {"node-a", "node-b", "node-c"}
    if not isinstance(records, list) or {item.get("node") for item in records} != expected:
        raise ValueError("Peer endpoint file must contain node-a, node-b and node-c.")
    if len({item.get("peer_id") for item in records}) != 3:
        raise ValueError("The three Kubo Peer IDs must be unique.")
    if any(not str(item.get("address", "")).startswith("/dns4/bore.pub/tcp/") for item in records):
        raise ValueError("Every peer endpoint must use the temporary bore.pub TCP tunnel.")
    return [item for item in records if item["node"] != local_role]


def create_request(service, node_label: str, btc_amount: str, asset: str, amount: str, network: str):
    result = service.create_btc_exchange_request(
        btc_amount=btc_amount,
        receive_asset=asset,
        receive_amount=amount,
        receive_network=network,
        description=f"Synthetic three-Ubuntu P2P acceptance request from {node_label}.",
        contacts=[{"type": "email", "value": f"{node_label}@example.invalid"}],
        publish_identity=False,
        defer_manifest=True,
    )
    document = json.loads(Path(result["request_path"]).read_text(encoding="utf-8"))
    return result, document


def received_event(protocol, event_type):
    with protocol._lock:
        return next((item for item in reversed(protocol._received) if item.get("type") == event_type), None)


def wait_for_peer_readiness(protocol, role, peer_id, timeout=60.0, soak_seconds=10.0):
    expected_roles = {"node-a", "node-b", "node-c"} - {role}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        protocol._publish("TEST_NODE_READY", node_role=role, peer_id=peer_id)
        with protocol._lock:
            ready_roles = {
                item.get("node_role")
                for item in protocol._received
                if item.get("type") == "TEST_NODE_READY"
            }
        if expected_roles.issubset(ready_roles):
            # Keep announcing during a short soak so late subscribers have a live listener
            # before the proposer starts the request-window timer.
            soak_deadline = time.monotonic() + soak_seconds
            while time.monotonic() < soak_deadline:
                protocol._publish("TEST_NODE_READY", node_role=role, peer_id=peer_id)
                time.sleep(1.0)
            return
        time.sleep(1.0)
    raise AssertionError(f"{role} did not observe readiness announcements from {sorted(expected_roles)}.")


def wait_for_manifest_readiness(protocol, role, manifest_hash, event_type, timeout=60.0):
    expected_roles = {"node-a", "node-b", "node-c"}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        protocol._publish(event_type, node_role=role, manifest_hash=manifest_hash)
        with protocol._lock:
            ready_roles = {role} | {
                item.get("node_role")
                for item in protocol._received
                if item.get("type") == event_type and item.get("manifest_hash") == manifest_hash
            }
        if expected_roles.issubset(ready_roles):
            # A short final announcement window reduces asymmetric PubSub timing races.
            for _ in range(3):
                protocol._publish(event_type, node_role=role, manifest_hash=manifest_hash)
                time.sleep(0.5)
            return
        time.sleep(0.75)
    raise AssertionError(f"{role} did not observe all three acknowledgements for manifest {manifest_hash}.")


def wait_for_request(service, request_id, timeout=60.0, evidence=False):
    def ready():
        item = service.find_request(request_id)
        if not item:
            return False
        if evidence and not item.get("evidence"):
            return False
        return item
    return wait_until(f"request {request_id}" + (" and evidence" if evidence else ""), ready, timeout=timeout)


def print_protocol_diagnostics(role, protocol, service, context):
    manifest = service.current_manifest()
    with protocol._lock:
        received = list(protocol._received)
        listener_errors = list(protocol._listener_errors)
    relevant = [
        {
            "type": item.get("type"),
            "sender_node_id": item.get("sender_node_id"),
            "reply_to": item.get("reply_to"),
            "manifest_hash": item.get("manifest_hash"),
            "imported_count": item.get("imported_count"),
            "error": item.get("error"),
            "reason": item.get("reason"),
        }
        for item in received
        if item.get("type") in {"REQUEST_BATCH", "BATCH_ACK", "REQUEST_ACK", "TEST_REQUEST_PUBLISHED",
                                "TEST_INITIAL_MANIFEST_READY", "TEST_EVIDENCE_EXPECTED"}
    ][-40:]
    print(json.dumps({
        "diagnostic": context,
        "node": role,
        "manifest_hash": manifest.get("manifest_hash") if manifest else None,
        "manifest_sequence": manifest.get("sequence") if manifest else None,
        "manifest_request_count": len(manifest.get("requests", [])) if manifest else 0,
        "received_message_types": [item.get("type") for item in received[-60:]],
        "relevant_messages": relevant,
        "listener_errors": listener_errors[-20:],
    }, indent=2, sort_keys=True, default=str))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=("node-a", "node-b", "node-c"), required=True)
    parser.add_argument("--peer-file", required=True, type=Path)
    parser.add_argument("--summary", type=Path, default=None)
    args = parser.parse_args()

    role = args.role
    endpoints = load_peer_endpoints(args.peer_file, role)
    runtime = NodeRuntime()
    runtime.boot()

    local_identity = runtime.network.identity()
    profile = runtime.identity_profile.load()
    if not profile or profile.get("identity_status") != "declared":
        raise AssertionError(f"{role}: synthetic identity is not declared.")
    if profile.get("node_id") != local_identity.peer_id:
        raise AssertionError(f"{role}: identity is not associated with the current Kubo Peer ID.")
    if profile.get("document_number", "").startswith("REAL-"):
        raise AssertionError("Real document data is prohibited in this test.")

    for peer in endpoints:
        runtime.network.connect(peer["address"])

    expected_peer_ids = {peer["peer_id"] for peer in endpoints}
    def connected():
        current = set(runtime.network.connected_peers())
        return expected_peer_ids.issubset(current)
    wait_until(f"{role} connects to the other two independent Kubo nodes",
               connected, timeout=75.0)
    connected_peer_ids = set(runtime.network.connected_peers())
    if not expected_peer_ids.issubset(connected_peer_ids):
        raise AssertionError(f"{role} lost a peer connection after the wait: {connected_peer_ids!r}")

    service = P2PContractsService(runtime.storage, runtime.identity_profile, runtime.network)
    protocol = PropagationProtocol(runtime.storage, runtime.network, runtime.kubo, service=service)
    protocol.start()
    summary = {
        "node": role,
        "peer_id": local_identity.peer_id,
        "identity_id": profile["identity_id"],
        "identity_status": profile["identity_status"],
        "uid": os.getuid(),
        "connected_peer_ids": sorted(connected_peer_ids),
        "scenario": "cross-vm-p2p-contracts",
    }

    try:
        wait_for_peer_readiness(protocol, role, local_identity.peer_id)
        if role == "node-a":
            # Shorten the protocol's ten-minute window only inside this acceptance-test process.
            # Production defaults and installed source files are not changed.
            propagation_module.WINDOW_SECONDS = 45
            proposal = protocol.accept_new_propagation(None, require_owner_request=True)
            summary["proposal_id"] = proposal["proposal_id"]

            wait_until(
                "node B's request to be queued by node A",
                lambda: len(protocol._pending_requests) >= 1,
                timeout=35.0,
            )
            state = wait_until(
                "proposal window to become ready",
                lambda: protocol.current_state()
                if protocol.current_state() and protocol.current_state().get("status") == "READY_TO_SUBMIT"
                else False,
                timeout=60.0,
            )
            request_a, request_a_doc = create_request(
                service, "node-a", "0.025", "EUR", "700", "SEPA"
            )
            finalized = protocol.finalize_propagation(request_a_doc)
            manifest = service.current_manifest()
            if not manifest or len(manifest.get("requests", [])) != 2:
                raise AssertionError("Node A did not finalize both requests into one manifest.")
            request_b_id = protocol._pending_requests[0].get("request_id") if protocol._pending_requests else None
            # finalize_propagation clears pending state, so resolve B's request from the committed manifest.
            request_ids = [item.get("request_id") for item in manifest.get("requests", [])]
            if request_a["request_id"] not in request_ids or len(request_ids) != 2:
                raise AssertionError(f"Unexpected request batch: {request_ids!r}")
            request_b_id = next(item for item in request_ids if item != request_a["request_id"])
            protocol._publish(
                "TEST_REQUEST_PUBLISHED",
                request_a_id=request_a["request_id"],
                request_b_id=request_b_id,
                manifest_hash=manifest["manifest_hash"],
                request_ids=request_ids,
            )
            summary.update({
                "request_a_id": request_a["request_id"],
                "request_b_id": request_b_id,
                "initial_manifest_hash": manifest["manifest_hash"],
                "batch_request_count": finalized["batch_request_count"],
            })

        elif role == "node-b":
            proposal = wait_until(
                "active proposal from node A",
                lambda: next(
                    (item for item in protocol.query_status(wait_seconds=1.0).get("active_proposals", [])
                     if item.get("proposer_node_id") in expected_peer_ids),
                    False,
                ),
                timeout=70.0,
                interval=0.2,
            )
            if proposal.get("proposer_node_id") == local_identity.peer_id:
                raise AssertionError("Node B unexpectedly discovered its own proposal as remote.")
            request_b, request_b_doc = create_request(
                service, "node-b", "0.015", "USDT", "1000", "TRON"
            )
            acknowledgement = protocol.submit_request(proposal, request_b_doc, wait_seconds=12.0)
            if not acknowledgement.get("accepted"):
                raise AssertionError(f"Node A rejected node B's request: {acknowledgement!r}")
            summary["submitted_request_id"] = request_b["request_id"]
            event = wait_until(
                "node A's committed batch announcement",
                lambda: received_event(protocol, "TEST_REQUEST_PUBLISHED"),
                timeout=90.0,
            )
            if request_b["request_id"] != event.get("request_b_id"):
                raise AssertionError("Node A committed a different request than node B submitted.")
            summary["request_a_id"] = event["request_a_id"]
            summary["request_b_id"] = event["request_b_id"]
            summary["initial_manifest_hash"] = event["manifest_hash"]

        else:  # node-c
            event = wait_until(
                "node A's committed batch announcement",
                lambda: received_event(protocol, "TEST_REQUEST_PUBLISHED"),
                timeout=120.0,
            )
            summary["request_a_id"] = event["request_a_id"]
            summary["request_b_id"] = event["request_b_id"]
            summary["initial_manifest_hash"] = event["manifest_hash"]

        request_a_id = summary["request_a_id"]
        request_b_id = summary["request_b_id"]

        # Every remote node must import the same two-request manifest before proceeding.
        try:
            wait_for_request(service, request_a_id, timeout=75.0)
            wait_for_request(service, request_b_id, timeout=75.0)
        except AssertionError:
            print_protocol_diagnostics(role, protocol, service, "initial request batch failed to import")
            raise
        def matching_initial_manifest():
            manifest = service.current_manifest()
            if (
                manifest
                and len(manifest.get("requests", [])) == 2
                and manifest.get("manifest_hash") == summary["initial_manifest_hash"]
            ):
                return manifest
            return False

        initial_manifest = wait_until(
            "two-request manifest synchronization",
            matching_initial_manifest,
            timeout=75.0,
        )
        if len(initial_manifest.get("requests", [])) != 2:
            raise AssertionError(f"{role} did not import exactly two requests.")
        wait_for_manifest_readiness(
            protocol, role, summary["initial_manifest_hash"], "TEST_INITIAL_MANIFEST_READY"
        )

        if role == "node-c":
            evidence = service.create_request_evidence(
                request_id=request_a_id,
                outcome="exchange_completed",
                evidence_type="exchange_result",
                description="Synthetic evidence created by independent Ubuntu node C.",
                reporter_statement="Node C verified the cross-VM test scenario.",
                target_node_id=next(item["peer_id"] for item in load_peer_endpoints(args.peer_file, role)
                                    if item["node"] == "node-a"),
                rating=5,
            )
            evidence_path = runtime.storage.path("p2p_contracts/evidence") / f"{evidence['evidence_id']}.json"
            evidence_document = json.loads(evidence_path.read_text(encoding="utf-8"))
            published = protocol.publish_evidence(evidence_document, service.current_manifest(), wait_seconds=5.0)
            accepted = {
                item.get("sender_node_id")
                for item in published.get("peer_acknowledgements", [])
                if item.get("accepted") is True
            }
            if not expected_peer_ids.issubset(accepted):
                raise AssertionError(f"Node C did not receive positive evidence acknowledgements from A and B: {published!r}")
            final_manifest = service.current_manifest()
            protocol._publish(
                "TEST_EVIDENCE_EXPECTED",
                request_a_id=request_a_id,
                evidence_id=evidence["evidence_id"],
                manifest_hash=final_manifest["manifest_hash"],
            )
            summary["evidence_id"] = evidence["evidence_id"]
            summary["final_manifest_hash"] = final_manifest["manifest_hash"]

        else:
            event = wait_until(
                "node C's evidence convergence announcement",
                lambda: received_event(protocol, "TEST_EVIDENCE_EXPECTED"),
                timeout=90.0,
            )
            if event.get("request_a_id") != request_a_id:
                raise AssertionError("Evidence announcement refers to a different request.")
            summary["evidence_id"] = event["evidence_id"]
            summary["final_manifest_hash"] = event["manifest_hash"]

        def matching_final_manifest():
            manifest = service.current_manifest()
            found = service.find_request(request_a_id)
            if (
                manifest
                and manifest.get("manifest_hash") == summary["final_manifest_hash"]
                and found
                and found.get("request_status") == "exchange_completed"
                and any(
                    item.get("evidence_id") == summary["evidence_id"] and item.get("rating") == 5
                    for item in found.get("evidence", [])
                )
            ):
                return manifest
            return False

        final_manifest = wait_until(
            "identical final manifest and closure evidence",
            matching_final_manifest,
            timeout=90.0,
        )
        if final_manifest.get("manifest_hash") != summary["final_manifest_hash"]:
            raise AssertionError(f"{role}: final manifest hash did not converge.")
        summary["final_manifest_sequence"] = final_manifest["sequence"]
        summary["request_status"] = service.find_request(request_a_id)["request_status"]
        summary["evidence_verified"] = True

        # Scenario 2 rotates roles: B proposes, C submits, and A records closure evidence.
        propagation_module.WINDOW_SECONDS = 45
        if role == "node-b":
            parent_hash = service.current_manifest()["manifest_hash"]
            proposal2 = protocol.accept_new_propagation(parent_hash, require_owner_request=True)
            wait_until(
                "node C's request to be queued by node B",
                lambda: len(protocol._pending_requests) >= 1,
                timeout=35.0,
            )
            wait_until(
                "second proposal window to become ready",
                lambda: protocol.current_state()
                if protocol.current_state() and protocol.current_state().get("status") == "READY_TO_SUBMIT"
                else False,
                timeout=60.0,
            )
            request_b2, request_b2_doc = create_request(
                service, "node-b-round-2", "0.010", "ETH", "2", "ETHEREUM"
            )
            finalized2 = protocol.finalize_propagation(request_b2_doc)
            manifest2 = service.current_manifest()
            request_ids2 = [item.get("request_id") for item in manifest2.get("requests", [])]
            if (
                len(request_ids2) != 4
                or request_b2["request_id"] not in request_ids2
                or finalized2.get("batch_request_count") != 2
            ):
                raise AssertionError(f"Node B did not append a two-request batch to manifest sequence 2: {request_ids2!r}")
            request_c2_id = next(
                item for item in request_ids2
                if item != request_b2["request_id"]
                and item not in {request_a_id, request_b_id}
            )
            protocol._publish(
                "TEST_REQUEST_PUBLISHED_2",
                request_b2_id=request_b2["request_id"],
                request_c2_id=request_c2_id,
                manifest_hash=manifest2["manifest_hash"],
                request_ids=request_ids2,
            )
            summary["scenario2_request_b_id"] = request_b2["request_id"]
            summary["scenario2_request_c_id"] = request_c2_id
            summary["scenario2_initial_manifest_hash"] = manifest2["manifest_hash"]

        elif role == "node-c":
            proposal2 = wait_until(
                "active second proposal from node B",
                lambda: next(
                    (item for item in protocol.query_status(wait_seconds=1.0).get("active_proposals", [])
                     if item.get("proposer_node_id") in expected_peer_ids),
                    False,
                ),
                timeout=70.0,
                interval=0.2,
            )
            if proposal2.get("proposer_node_id") == local_identity.peer_id:
                raise AssertionError("Node C unexpectedly discovered its own second proposal as remote.")
            request_c2, request_c2_doc = create_request(
                service, "node-c-round-2", "0.008", "USDC", "300", "POLYGON"
            )
            acknowledgement2 = protocol.submit_request(proposal2, request_c2_doc, wait_seconds=12.0)
            if not acknowledgement2.get("accepted"):
                raise AssertionError(f"Node B rejected node C's second request: {acknowledgement2!r}")
            event2 = wait_until(
                "node B's committed second batch announcement",
                lambda: received_event(protocol, "TEST_REQUEST_PUBLISHED_2"),
                timeout=90.0,
            )
            if request_c2["request_id"] != event2.get("request_c2_id"):
                raise AssertionError("Node B committed a different request than node C submitted.")
            summary["scenario2_request_b_id"] = event2["request_b2_id"]
            summary["scenario2_request_c_id"] = event2["request_c2_id"]
            summary["scenario2_initial_manifest_hash"] = event2["manifest_hash"]

        else:  # node-a observes the second batch
            event2 = wait_until(
                "node B's committed second batch announcement",
                lambda: received_event(protocol, "TEST_REQUEST_PUBLISHED_2"),
                timeout=120.0,
            )
            summary["scenario2_request_b_id"] = event2["request_b2_id"]
            summary["scenario2_request_c_id"] = event2["request_c2_id"]
            summary["scenario2_initial_manifest_hash"] = event2["manifest_hash"]

        request_b2_id = summary["scenario2_request_b_id"]
        request_c2_id = summary["scenario2_request_c_id"]
        wait_for_request(service, request_b2_id, timeout=75.0)
        wait_for_request(service, request_c2_id, timeout=75.0)

        def matching_second_manifest():
            manifest = service.current_manifest()
            if (
                manifest
                and len(manifest.get("requests", [])) == 4
                and manifest.get("manifest_hash") == summary["scenario2_initial_manifest_hash"]
            ):
                return manifest
            return False

        second_manifest = wait_until(
            "second four-request manifest synchronization",
            matching_second_manifest,
            timeout=75.0,
        )
        if len(second_manifest.get("requests", [])) != 4:
            raise AssertionError(f"{role} did not import the four-request manifest for scenario 2.")
        wait_for_manifest_readiness(
            protocol, role, summary["scenario2_initial_manifest_hash"], "TEST_SCENARIO2_MANIFEST_READY"
        )

        if role == "node-a":
            evidence2 = service.create_request_evidence(
                request_id=request_b2_id,
                outcome="exchange_completed",
                evidence_type="exchange_result",
                description="Synthetic evidence created by independent Ubuntu node A in scenario 2.",
                reporter_statement="Node A verified the rotated-proposer cross-VM scenario.",
                target_node_id=next(item["peer_id"] for item in load_peer_endpoints(args.peer_file, role)
                                    if item["node"] == "node-b"),
                rating=5,
            )
            evidence_path2 = runtime.storage.path("p2p_contracts/evidence") / f"{evidence2['evidence_id']}.json"
            evidence_document2 = json.loads(evidence_path2.read_text(encoding="utf-8"))
            published2 = protocol.publish_evidence(
                evidence_document2, service.current_manifest(), wait_seconds=5.0
            )
            accepted2 = {
                item.get("sender_node_id")
                for item in published2.get("peer_acknowledgements", [])
                if item.get("accepted") is True
            }
            if not expected_peer_ids.issubset(accepted2):
                raise AssertionError(
                    f"Node A did not receive positive evidence acknowledgements from B and C: {published2!r}"
                )
            final_manifest2 = service.current_manifest()
            protocol._publish(
                "TEST_EVIDENCE_EXPECTED_2",
                request_b2_id=request_b2_id,
                evidence_id=evidence2["evidence_id"],
                manifest_hash=final_manifest2["manifest_hash"],
            )
            summary["scenario2_evidence_id"] = evidence2["evidence_id"]
            summary["scenario2_final_manifest_hash"] = final_manifest2["manifest_hash"]
        else:
            event_evidence2 = wait_until(
                "node A's second evidence convergence announcement",
                lambda: received_event(protocol, "TEST_EVIDENCE_EXPECTED_2"),
                timeout=90.0,
            )
            if event_evidence2.get("request_b2_id") != request_b2_id:
                raise AssertionError("Second evidence announcement refers to a different request.")
            summary["scenario2_evidence_id"] = event_evidence2["evidence_id"]
            summary["scenario2_final_manifest_hash"] = event_evidence2["manifest_hash"]

        def matching_second_final_manifest():
            manifest = service.current_manifest()
            found = service.find_request(request_b2_id)
            if (
                manifest
                and manifest.get("manifest_hash") == summary["scenario2_final_manifest_hash"]
                and found
                and found.get("request_status") == "exchange_completed"
                and any(
                    item.get("evidence_id") == summary["scenario2_evidence_id"] and item.get("rating") == 5
                    for item in found.get("evidence", [])
                )
            ):
                return manifest
            return False

        final_manifest2 = wait_until(
            "scenario 2 manifest and closure evidence convergence",
            matching_second_final_manifest,
            timeout=90.0,
        )
        summary["scenario2_final_manifest_sequence"] = final_manifest2["sequence"]
        summary["scenario2_request_status"] = service.find_request(request_b2_id)["request_status"]
        summary["scenario2_evidence_verified"] = True
        summary["connected_peer_ids"] = sorted(set(runtime.network.connected_peers()))
        summary["result"] = "PASS"

        if args.summary:
            args.summary.parent.mkdir(parents=True, exist_ok=True)
            args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2, sort_keys=True))
    finally:
        protocol.stop()


if __name__ == "__main__":
    main()
