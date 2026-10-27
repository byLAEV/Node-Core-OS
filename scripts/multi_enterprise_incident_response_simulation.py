#!/usr/bin/env python3
"""Synthetic multi-enterprise incident response simulation.

This program uses in-memory test identities only. It does not contact real
networks, scan domains, generate attack traffic, or modify external assets.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def public_key_bytes(key: Ed25519PublicKey) -> bytes:
    return key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def public_key_hex(key: Ed25519PublicKey) -> str:
    return public_key_bytes(key).hex()


def sign(key: Ed25519PrivateKey, payload: dict[str, Any]) -> str:
    return key.sign(canonical_json(payload)).hex()


def verify(public_key: str, payload: dict[str, Any], signature: str) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key)).verify(
            bytes.fromhex(signature), canonical_json(payload)
        )
        return True
    except (ValueError, InvalidSignature, TypeError):
        return False


@dataclass
class EnterprisePool:
    pool_id: str
    private_key: Ed25519PrivateKey = field(default_factory=Ed25519PrivateKey.generate)
    assets: dict[str, dict[str, Any]] = field(default_factory=dict)
    seen_event_ids: set[str] = field(default_factory=set)
    audit_log: list[dict[str, Any]] = field(default_factory=list)

    @property
    def public_key(self) -> str:
        return public_key_hex(self.private_key.public_key())

    def issue_certificate(self, asset_id: str, asset_type: str, asset_public_key: str,
                          now: int | None = None, lifetime_seconds: int = 86400) -> dict[str, Any]:
        current = int(time.time()) if now is None else now
        if lifetime_seconds <= 0:
            raise ValueError("Certificate lifetime must be positive")
        claims = {
            "schema": "node-core-os.enterprise-certificate.v1",
            "certificate_id": "cert-" + uuid.uuid4().hex,
            "issuer_pool_id": self.pool_id,
            "asset_id": asset_id,
            "asset_type": asset_type,
            "asset_public_key": asset_public_key,
            "issued_at": current,
            "expires_at": current + lifetime_seconds,
            "status": "active",
        }
        return {"claims": claims, "signature": sign(self.private_key, claims)}

    def verify_certificate(self, certificate: dict[str, Any], now: int | None = None) -> bool:
        claims = certificate.get("claims", {})
        current = int(time.time()) if now is None else now
        return (
            claims.get("issuer_pool_id") == self.pool_id
            and claims.get("status") == "active"
            and isinstance(claims.get("issued_at"), int)
            and isinstance(claims.get("expires_at"), int)
            and claims["issued_at"] <= current < claims["expires_at"]
            and verify(self.public_key, claims, certificate.get("signature", ""))
        )

    def register_installation(self, report: dict[str, Any], certificate: dict[str, Any],
                              now: int | None = None) -> str:
        payload = report.get("payload", {})
        claims = certificate.get("claims", {})
        if not self.verify_certificate(certificate, now=now):
            raise ValueError("Certificate is invalid, expired, or issued by another pool")
        if payload.get("issuer_pool_id") != self.pool_id:
            raise PermissionError("Cross-pool registration denied")
        if payload.get("asset_id") != claims.get("asset_id"):
            raise ValueError("Report asset does not match certificate")
        if payload.get("certificate_id") != claims.get("certificate_id"):
            raise ValueError("Report certificate ID mismatch")
        if not verify(claims.get("asset_public_key", ""), payload, report.get("signature", "")):
            raise ValueError("Installation report signature is invalid")
        event_id = payload.get("event_id")
        if not event_id:
            raise ValueError("Missing event ID")
        if event_id in self.seen_event_ids:
            return "duplicate_ignored"
        self.seen_event_ids.add(event_id)
        self.assets[claims["asset_id"]] = {
            "certificate_id": claims["certificate_id"],
            "asset_type": claims["asset_type"],
            "status": "registered",
        }
        self.audit_log.append({"event_id": event_id, "result": "registered", "asset_id": claims["asset_id"]})
        return "registered"

    def accept_incident(self, request: dict[str, Any], certificate: dict[str, Any],
                        now: int | None = None) -> str:
        payload = request.get("payload", {})
        claims = certificate.get("claims", {})
        if not self.verify_certificate(certificate, now=now):
            raise ValueError("Incident certificate is invalid or expired")
        if payload.get("issuer_pool_id") != self.pool_id:
            raise PermissionError("Incident routed to the wrong enterprise pool")
        if payload.get("asset_id") != claims.get("asset_id"):
            raise PermissionError("Incident asset is not bound to this certificate")
        if payload.get("certificate_id") != claims.get("certificate_id"):
            raise PermissionError("Incident certificate mismatch")
        if not verify(claims.get("asset_public_key", ""), payload, request.get("signature", "")):
            raise ValueError("Incident signature is invalid")
        event_id = payload.get("event_id")
        if not event_id:
            raise ValueError("Missing incident event ID")
        if event_id in self.seen_event_ids:
            return "duplicate_ignored"
        self.seen_event_ids.add(event_id)
        self.audit_log.append({
            "event_id": event_id,
            "result": "incident_accepted",
            "asset_id": payload["asset_id"],
            "incident_type": payload["incident_type"],
        })
        return "incident_accepted"


class EnterpriseAsset:
    def __init__(self, asset_id: str, owner_pool_id: str, asset_type: str):
        self.asset_id = asset_id
        self.owner_pool_id = owner_pool_id
        self.asset_type = asset_type
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = public_key_hex(self.private_key.public_key())
        self.certificate: dict[str, Any] | None = None

    def install(self, certificate: dict[str, Any]) -> dict[str, Any]:
        claims = certificate.get("claims", {})
        if claims.get("asset_id") != self.asset_id or claims.get("asset_public_key") != self.public_key:
            raise PermissionError("Certificate does not belong to this asset and key")
        if claims.get("issuer_pool_id") != self.owner_pool_id:
            raise PermissionError("Certificate issuer does not match asset owner pool")
        self.certificate = certificate
        payload = {
            "schema": "node-core-os.installation-report.v1",
            "event_id": "install-" + uuid.uuid4().hex,
            "event_type": "certificate_installed",
            "asset_id": self.asset_id,
            "certificate_id": claims["certificate_id"],
            "issuer_pool_id": self.owner_pool_id,
            "reported_at": int(time.time()),
        }
        return {"payload": payload, "signature": sign(self.private_key, payload)}

    def report_incident(self, incident_type: str, evidence: str) -> dict[str, Any]:
        if self.certificate is None:
            raise ValueError("No certificate installed")
        claims = self.certificate["claims"]
        payload = {
            "schema": "node-core-os.incident-request.v1",
            "event_id": "incident-" + uuid.uuid4().hex,
            "event_type": "synthetic_incident",
            "asset_id": self.asset_id,
            "certificate_id": claims["certificate_id"],
            "issuer_pool_id": self.owner_pool_id,
            "incident_type": incident_type,
            "evidence_sha256": hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
            "reported_at": int(time.time()),
        }
        return {"payload": payload, "signature": sign(self.private_key, payload)}


@dataclass
class IdentityNode:
    node_id: str
    private_key: Ed25519PrivateKey = field(default_factory=Ed25519PrivateKey.generate)

    @property
    def public_key(self) -> str:
        return public_key_hex(self.private_key.public_key())

    def assess(self, incident_digest: str, recommendation: str) -> dict[str, Any]:
        payload = {
            "node_id": self.node_id,
            "incident_digest": incident_digest,
            "recommendation": recommendation,
        }
        return {"payload": payload, "signature": sign(self.private_key, payload)}


def verify_quorum(votes: list[dict[str, Any]], trusted_nodes: dict[str, str],
                  incident_digest: str, threshold: int = 2) -> bool:
    if threshold < 2:
        raise ValueError("Quorum threshold must be at least two distinct nodes")
    accepted_nodes: set[str] = set()
    for vote in votes:
        payload = vote.get("payload", {})
        node_id = payload.get("node_id", "")
        if (
            node_id in trusted_nodes
            and payload.get("incident_digest") == incident_digest
            and payload.get("recommendation") == "containment_recommended"
            and verify(trusted_nodes[node_id], payload, vote.get("signature", ""))
        ):
            accepted_nodes.add(node_id)
    return len(accepted_nodes) >= threshold


def run_simulation() -> dict[str, Any]:
    """Run two independent enterprise pools and one synthetic incident."""
    pool_a = EnterprisePool("enterprise-pool-A")
    pool_b = EnterprisePool("enterprise-pool-B")
    asset_a = EnterpriseAsset("web2:alpha.example.test", pool_a.pool_id, "web2_domain")
    asset_b = EnterpriseAsset("device:beta-edge-001", pool_b.pool_id, "device")

    certificate_a = pool_a.issue_certificate(asset_a.asset_id, asset_a.asset_type, asset_a.public_key)
    certificate_b = pool_b.issue_certificate(asset_b.asset_id, asset_b.asset_type, asset_b.public_key)
    asset_a.install(certificate_a)
    asset_b.install(certificate_b)
    install_report_a = asset_a.install(certificate_a)
    install_report_b = asset_b.install(certificate_b)
    registration_a = pool_a.register_installation(install_report_a, certificate_a)
    registration_b = pool_b.register_installation(install_report_b, certificate_b)

    # Re-delivery of the same authenticated event must not create a second record.
    duplicate_result = pool_a.register_installation(install_report_a, certificate_a)

    incident = asset_a.report_incident("synthetic_http_flood_indicator", "synthetic-test-evidence-001")
    incident_result = pool_a.accept_incident(incident, certificate_a)
    incident_digest = hashlib.sha256(canonical_json(incident["payload"])).hexdigest()

    nodes = [IdentityNode("identity-node-1"), IdentityNode("identity-node-2"), IdentityNode("identity-node-3")]
    trusted = {node.node_id: node.public_key for node in nodes}
    votes = [node.assess(incident_digest, "containment_recommended") for node in nodes[:2]]
    quorum = verify_quorum(votes, trusted, incident_digest, threshold=2)

    # Deliberately altered evidence must not verify as an authenticated report.
    tampered_incident = {"payload": dict(incident["payload"]), "signature": incident["signature"]}
    tampered_incident["payload"]["incident_type"] = "different_untrusted_claim"
    tamper_rejected = False
    try:
        pool_a.accept_incident(tampered_incident, certificate_a)
    except ValueError:
        tamper_rejected = True

    return {
        "simulation": "Node Core OS byLAEV — multi-enterprise incident response",
        "mode": "synthetic_in_memory_only",
        "external_network_contacted": False,
        "real_assets_modified": False,
        "enterprise_pools": 2,
        "registered_assets": len(pool_a.assets) + len(pool_b.assets),
        "pool_a_installation": registration_a,
        "pool_b_installation": registration_b,
        "duplicate_event_result": duplicate_result,
        "duplicate_registration_count": len(pool_a.assets),
        "incident_result": incident_result,
        "trusted_identity_nodes": len(trusted),
        "valid_distinct_votes": len(votes),
        "quorum_threshold": 2,
        "quorum_reached": quorum,
        "tampered_incident_rejected": tamper_rejected,
        "simulated_response": "containment_recommended" if quorum else "manual_review_required",
        "response_applied_to_real_asset": False,
        "security_boundary": (
            "A quorum is only a signed recommendation in this simulation. No live mitigation is performed. "
            "Production trust enrollment, persistence, revocation, anti-replay across restarts, transport, "
            "and independent-organization validation remain out of scope."
        ),
    }


if __name__ == "__main__":
    result = run_simulation()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not (
        result["registered_assets"] == 2
        and result["duplicate_event_result"] == "duplicate_ignored"
        and result["incident_result"] == "incident_accepted"
        and result["quorum_reached"]
        and result["tampered_incident_rejected"]
        and not result["response_applied_to_real_asset"]
    ):
        raise SystemExit("Simulation acceptance criteria failed")
