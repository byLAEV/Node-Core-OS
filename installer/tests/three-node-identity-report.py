#!/usr/bin/env python3
"""End-to-end identity-presence/report synchronization across three live Kubo nodes.

This test uses independent Kubo repositories and real Kubo RPC/CLI operations.
Identity profile values are synthetic fixtures and must never be published.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from node_core.identity.profile import IdentityProfileStore
from node_core.identity_presence import IdentityPresence
from node_core.ipfs import KuboManager
from node_core.network import NodeNetwork


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kubo", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--evidence-dir", required=True)
    for label in ("a", "b", "c"):
        parser.add_argument(f"--repo-{label}", required=True)
        parser.add_argument(f"--api-{label}", required=True)
    args = parser.parse_args()

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    labels = ("a", "b", "c")
    services = {}
    networks = {}
    kubos = {}
    profiles = {}

    for label in labels:
        kubo = KuboManager(
            executable=args.kubo,
            repo_path=Path(getattr(args, f"repo_{label}")),
            api=getattr(args, f"api_{label}"),
            profile="",
        )
        network = NodeNetwork(kubo)
        profile = IdentityProfileStore(work_dir / f"identity-profile-{label}")
        # Synthetic values ensure this integration test never uses real personal data.
        profile.save_declared_profile(
            full_name=f"Integration Test Node {label.upper()}",
            issuing_country="ZZ",
            document_type="TEST",
            document_number=f"TEST-PRIVATE-NUMBER-{label.upper()}",
        )
        node_id = network.identity().peer_id
        profile.associate_node(node_id)
        services[label] = IdentityPresence(
            work_dir / f"node-data-{label}", profile, network, kubo
        )
        networks[label] = network
        kubos[label] = kubo
        profiles[label] = profile

    node_ids = {label: networks[label].identity().peer_id for label in labels}
    require(len(set(node_ids.values())) == 3, "The three Kubo nodes must have distinct public peer IDs.")
    for label in labels:
        peers = set(networks[label].connected_peers())
        expected = set(node_ids.values()) - {node_ids[label]}
        require(expected.issubset(peers), f"Node {label.upper()} is not connected to both other nodes.")

    announcement_cids = {}
    for label in labels:
        published = services[label].publish_announcement()
        require(published["node_id"] == node_ids[label], f"Node {label.upper()} published the wrong node ID.")
        require(published["pinned_locally"], f"Node {label.upper()} did not pin its announcement.")
        require(published["cid"] in kubos[label].pin_list(), f"Node {label.upper()} announcement pin is missing.")
        announcement_cids[label] = published["cid"]
        print(f"PASS: node {label.upper()} published and pinned its declaration | PeerID={node_ids[label]} | CID={published['cid']}")

    for receiver in labels:
        for publisher in labels:
            if publisher == receiver:
                continue
            imported = services[receiver].import_announcement(announcement_cids[publisher])
            require(
                imported["node_id"] == node_ids[publisher],
                f"Node {receiver.upper()} imported an incorrect declaration for node {publisher.upper()}.",
            )
        all_announcements = services[receiver]._all_announcements()
        require(len(all_announcements) == 3, f"Node {receiver.upper()} does not have all three declarations.")
        require(
            {item["node_id"] for item in all_announcements} == set(node_ids.values()),
            f"Node {receiver.upper()} has an incorrect declaration set.",
        )
        require(
            all(item["identity_associated"] is True for item in all_announcements),
            f"Node {receiver.upper()} did not receive all three positive association declarations.",
        )
        print(f"PASS: node {receiver.upper()} imported and stored all three declarations.")

    # Node A creates the canonical shared report from declarations actually received.
    report = services["a"].create_report()
    require(report["known_nodes"] == 3, "The shared report must count exactly three unique nodes.")
    require(report["connected_nodes"] == 3, "The shared report must count all three connected nodes.")
    require(report["identity_associations_announced"] == 3, "The shared report must count three association announcements.")
    require(report["identity_documents_transmitted"] == 0, "The report must state zero identity documents transmitted.")
    require(report["personal_identity_fields_transmitted"] == 0, "The report must state zero personal identity fields transmitted.")
    require(len({item["node_id"] for item in report["announcements"]}) == 3, "The report contains duplicate node declarations.")

    report_state = services["a"].publish_report()
    report_cid = report_state["report_cid"]
    canonical_bytes = services["a"].current_report_path.read_bytes()
    canonical_hash = sha256(canonical_bytes)
    require(report_cid in kubos["a"].pin_list(), "Node A report CID is not pinned.")
    print(f"PASS: node A published canonical report | Reference={report_state['report_reference_id']} | CID={report_cid} | SHA-256={canonical_hash}")

    for receiver in ("b", "c"):
        state = services[receiver].import_report(report_cid)
        local_bytes = services[receiver].current_report_path.read_bytes()
        require(local_bytes == canonical_bytes, f"Node {receiver.upper()} report bytes differ from node A.")
        require(sha256(local_bytes) == canonical_hash, f"Node {receiver.upper()} report SHA-256 differs from node A.")
        require(state["report_cid"] == report_cid, f"Node {receiver.upper()} recorded a different report CID.")
        require(report_cid in kubos[receiver].pin_list(), f"Node {receiver.upper()} report CID is not pinned in its own Kubo repository.")
        print(f"PASS: node {receiver.upper()} imported, stored byte-identical report, and verified local pin | CID={report_cid} | SHA-256={canonical_hash}")

    # All three nodes must expose the same reference, CID and exact local bytes.
    report_paths = {label: services[label].current_report_path for label in labels}
    local_bytes = {label: path.read_bytes() for label, path in report_paths.items()}
    require(all(content == canonical_bytes for content in local_bytes.values()), "The three local report files are not byte-identical.")
    for label in labels:
        state = services[label]._read_json(services[label].state_path)
        require(state["report_cid"] == report_cid, f"Node {label.upper()} state has a different report CID.")
        require(state["report_reference_id"] == report_state["report_reference_id"], f"Node {label.upper()} state has a different report reference.")
        require(report_cid in kubos[label].pin_list(), f"Node {label.upper()} does not independently report the canonical CID as pinned.")
        report_text = local_bytes[label].decode("utf-8")
        require("TEST-PRIVATE-NUMBER" not in report_text, f"Private test profile data leaked into node {label.upper()}'s report.")
        require("Integration Test Node" not in report_text, f"Private test profile name leaked into node {label.upper()}'s report.")

    evidence = {
        "result": "passed",
        "nodes": {label.upper(): node_ids[label] for label in labels},
        "announcement_cids": {label.upper(): announcement_cids[label] for label in labels},
        "report_reference_id": report_state["report_reference_id"],
        "report_cid": report_cid,
        "report_sha256": canonical_hash,
        "report_bytes_identical_on_all_nodes": True,
        "report_pinned_on_all_nodes": True,
        "known_nodes": report["known_nodes"],
        "connected_nodes": report["connected_nodes"],
        "identity_associations_announced": report["identity_associations_announced"],
        "identity_documents_transmitted": report["identity_documents_transmitted"],
        "personal_identity_fields_transmitted": report["personal_identity_fields_transmitted"],
    }
    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / "summary.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    for label in labels:
        node_evidence = evidence_dir / f"node-{label.upper()}"
        node_evidence.mkdir(parents=True, exist_ok=True)
        shutil.copy2(services[label].current_report_path, node_evidence / "current-report.json")
        shutil.copy2(services[label].state_path, node_evidence / "state.json")
        for source_dir_name in ("announcements", "incoming"):
            source_dir = services[label].root / source_dir_name
            target_dir = node_evidence / source_dir_name
            if source_dir.is_dir():
                shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
    print("PASS: all three real Kubo nodes have the same local report bytes, report reference, and independently verified local pin.")
    print(f"PASS: machine-readable evidence and each node's local report/state/declarations copied to {evidence_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: three-node identity/report synchronization failed: {exc}", file=sys.stderr)
        raise
