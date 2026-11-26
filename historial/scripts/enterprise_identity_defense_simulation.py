#!/usr/bin/env python3
"""Safe, synthetic simulation of enterprise certificate lifecycle and peer defense.

No external hosts are contacted. No real certificates, keys, domains, or devices
are read. All actions and attack indicators are generated in memory.
"""
from __future__ import annotations

import json
import hashlib
import time
import uuid
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def public_key_hex(key: Ed25519PublicKey) -> str:
    return key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def sign(private_key: Ed25519PrivateKey, payload: dict[str, Any]) -> str:
    return private_key.sign(canonical_json(payload)).hex()


def verify(public_key_hex_value: str, payload: dict[str, Any], signature: str) -> bool:
    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex_value))
        public_key.verify(bytes.fromhex(signature), canonical_json(payload))
        return True
    except (ValueError, InvalidSignature):
        return False


@dataclass
class EnterprisePool:
    pool_id: str
    private_key: Ed25519PrivateKey

    @property
    def public_key(self) -> str:
        return public_key_hex(self.private_key.public_key())

    def issue_certificate(self, asset_id: str, asset_type: str, asset_public_key: str,
                          security_profile: str, now: int | None = None) -> dict[str, Any]:
        issued_at = int(time.time()) if now is None else now
        claims = {
            "schema": "node-core-os.enterprise-certificate.v1",
            "certificate_id": "cert-" + uuid.uuid4().hex,
            "issuer_pool_id": self.pool_id,
            "asset_id": asset_id,
            "asset_type": asset_type,
            "asset_public_key": asset_public_key,
            "security_profile": security_profile,
            "issued_at": issued_at,
            "expires_at": issued_at + 86400,
            "status": "active",
        }
        return {"claims": claims, "issuer_signature": sign(self.private_key, claims)}

    def verify_certificate(self, certificate: dict[str, Any], now: int | None = None) -> bool:
        claims = certificate.get("claims", {})
        current = int(time.time()) if now is None else now
        return (
            claims.get("issuer_pool_id") == self.pool_id
            and claims.get("status") == "active"
            and claims.get("issued_at", current + 1) <= current
            and claims.get("expires_at", 0) > current
            and verify(self.public_key, claims, certificate.get("issuer_signature", ""))
        )


class EnterpriseAsset:
    def __init__(self, asset_id: str):
        self.asset_id = asset_id
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = public_key_hex(self.private_key.public_key())
        self.certificate: dict[str, Any] | None = None

    def install(self, certificate: dict[str, Any]) -> dict[str, Any]:
        claims = certificate.get("claims", {})
        if claims.get("asset_id") != self.asset_id or claims.get("asset_public_key") != self.public_key:
            raise ValueError("Certificate does not belong to this asset/key")
        self.certificate = certificate
        report = {
            "event_id": "install-" + uuid.uuid4().hex,
            "event_type": "certificate_installed",
            "asset_id": self.asset_id,
            "certificate_id": claims["certificate_id"],
            "issuer_pool_id": claims["issuer_pool_id"],
            "reported_at": int(time.time()),
        }
        return {"payload": report, "signature": sign(self.private_key, report)}

    def report_attack(self, attack_type: str, evidence: str) -> dict[str, Any]:
        if self.certificate is None:
            raise ValueError("Asset has no installed certificate")
        payload = {
            "event_id": "incident-" + uuid.uuid4().hex,
            "event_type": "synthetic_attack_detected",
            "asset_id": self.asset_id,
            "certificate_id": self.certificate["claims"]["certificate_id"],
            "issuer_pool_id": self.certificate["claims"]["issuer_pool_id"],
            "attack_type": attack_type,
            "evidence_sha256": hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
            "reported_at": int(time.time()),
        }
        return {"payload": payload, "signature": sign(self.private_key, payload)}


@dataclass
class IdentityNode:
    node_id: str
    private_key: Ed25519PrivateKey

    @property
    def public_key(self) -> str:
        return public_key_hex(self.private_key.public_key())

    def vote(self, incident_digest: str, decision: str) -> dict[str, str]:
        payload = {"node_id": self.node_id, "incident_digest": incident_digest, "decision": decision}
        return {"payload": payload, "signature": sign(self.private_key, payload)}


def verify_asset_report(report: dict[str, Any], certificate: dict[str, Any],
                        pool: EnterprisePool, now: int | None = None) -> bool:
    payload = report.get("payload", {})
    claims = certificate.get("claims", {})
    return (
        pool.verify_certificate(certificate, now=now)
        and payload.get("asset_id") == claims.get("asset_id")
        and payload.get("certificate_id") == claims.get("certificate_id")
        and payload.get("issuer_pool_id") == pool.pool_id
        and verify(claims.get("asset_public_key", ""), payload, report.get("signature", ""))
    )


def verify_node_votes(votes: list[dict[str, Any]], trusted_nodes: dict[str, str],
                      incident_digest: str, threshold: int = 2) -> bool:
    if threshold < 2:
        raise ValueError("Quorum threshold must be at least 2")
    accepted: set[str] = set()
    for vote in votes:
        payload = vote.get("payload", {})
        node_id = payload.get("node_id", "")
        if (node_id in trusted_nodes
                and payload.get("incident_digest") == incident_digest
                and payload.get("decision") == "containment_recommended"
                and verify(trusted_nodes[node_id], payload, vote.get("signature", ""))):
            accepted.add(node_id)
    return len(accepted) >= threshold


def run_simulation() -> dict[str, Any]:
    """Run a complete in-memory lifecycle with one pool, two assets and three peers."""
    pool = EnterprisePool("pool-enterprise-demo", Ed25519PrivateKey.generate())
    assets = [
        EnterpriseAsset("web2:portal.example.test"),
        EnterpriseAsset("device:edge-001"),
    ]
    installed_reports = []
    certificates = []
    for asset, asset_type, profile in (
        (assets[0], "web2_domain", "tls_and_application"),
        (assets[1], "device", "endpoint_integrity"),
    ):
        certificate = pool.issue_certificate(asset.asset_id, asset_type, asset.public_key, profile)
        if not pool.verify_certificate(certificate):
            raise RuntimeError("Issued certificate failed verification")
        report = asset.install(certificate)
        if not verify_asset_report(report, certificate, pool):
            raise RuntimeError("Installation report failed verification")
        certificates.append(certificate)
        installed_reports.append(report)

    incident = assets[0].report_attack("synthetic_http_flood_indicator", "synthetic-event-burst-001")
    if not verify_asset_report(incident, certificates[0], pool):
        raise RuntimeError("Incident report failed verification")

    peers = [IdentityNode(f"identity-node-{index}", Ed25519PrivateKey.generate()) for index in range(1, 4)]
    incident_digest = hashlib.sha256(canonical_json(incident["payload"])).hexdigest()
    votes = [peer.vote(incident_digest, "containment_recommended") for peer in peers[:2]]
    trusted_nodes = {peer.node_id: peer.public_key for peer in peers}
    quorum_reached = verify_node_votes(votes, trusted_nodes, incident_digest, threshold=2)

    result = {
        "simulation": "Node Core OS byLAEV — enterprise identity and coordinated defense",
        "mode": "synthetic_in_memory_only",
        "external_network_contacted": False,
        "real_assets_touched": False,
        "enterprise_pool": pool.pool_id,
        "assets_registered": len(installed_reports),
        "installation_reports_verified": sum(
            verify_asset_report(report, cert, pool)
            for report, cert in zip(installed_reports, certificates)
        ),
        "attack_report_verified": True,
        "trusted_identity_nodes": len(trusted_nodes),
        "valid_distinct_votes": len(votes),
        "quorum_threshold": 2,
        "quorum_reached": quorum_reached,
        "simulated_response": "containment_recommended" if quorum_reached else "escalate_without_automatic_global_action",
        "security_boundary": (
            "This proves only the synthetic workflow and cryptographic checks in this test. "
            "It does not demonstrate live network protection or block traffic."
        ),
    }
    if not quorum_reached or result["installation_reports_verified"] != 2:
        raise RuntimeError("Simulation acceptance criteria failed")
    return result


if __name__ == "__main__":
    print(json.dumps(run_simulation(), indent=2, ensure_ascii=False))
