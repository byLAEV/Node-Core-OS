#!/usr/bin/env python3
"""Deterministic, local-only attack simulations for the intent certificate prototype.

No sockets, live targets, or external systems are contacted. Results describe this
prototype only and are not evidence of production attack prevention.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from typing import Any

from intent_certificate_simulator import (
    IntentCertificateSimulator,
    build_demo_chain,
    signed_certificate,
)

NOW = "2026-10-25T12:00:00Z"


def make_client_chain(number: int) -> dict[str, dict[str, Any]]:
    suffix = f"{number:04d}"
    general_id, specific_id, demo_id = (
        f"general-{suffix}", f"specific-{suffix}", f"demo-{suffix}"
    )
    common = {
        "issuer": "synthetic-test-policy",
        "subject": f"synthetic-client-{suffix}",
        "intent": "monitor_availability",
        "scope": {"resources": ["/status"], "operations": ["GET"]},
        "issued_at": "2026-01-01T00:00:00Z",
        "expires_at": "2027-01-01T00:00:00Z",
        "status": "active",
    }
    general = signed_certificate(
        **common, certificate_id=general_id, certificate_type="general",
        parent_certificate_id=None,
    )
    specific = signed_certificate(
        **common, certificate_id=specific_id, certificate_type="specific",
        parent_certificate_id=general_id,
    )
    demonstration = signed_certificate(
        **common, certificate_id=demo_id, certificate_type="demonstration",
        parent_certificate_id=specific_id,
        demonstration={
            "purpose": "Check service status",
            "justification": "A status endpoint is required to measure availability.",
            "request_id": f"family-{suffix}",
        },
        limits={"requests_per_minute": 3},
    )
    return {c["certificate_id"]: c for c in (general, specific, demonstration)}


def request(cert_id: str, request_id: str, *, resource: str = "/status",
            operation: str = "GET", intent: str = "monitor_availability",
            second: int = 0) -> dict[str, str]:
    return {
        "request_id": request_id,
        "certificate_id": cert_id,
        "intent": intent,
        "resource": resource,
        "operation": operation,
        "timestamp": f"2026-10-25T12:00:{second:02d}Z",
    }


def run_attack_simulation() -> dict[str, Any]:
    scenarios: list[dict[str, Any]] = []

    # 1: direct scope escalation.
    sim = IntentCertificateSimulator(build_demo_chain())
    decision = sim.evaluate(request("demo-proof-001", "scope-attack", resource="/admin"))
    scenarios.append({
        "id": "A1_SCOPE_ESCALATION",
        "description": "One certificate requests /admin outside its /status scope.",
        "expected": "DENY",
        "observed": decision.outcome,
        "reason": decision.reason,
        "contained": decision.outcome == "DENY",
    })

    # 2: forged/tampered certificate payload.
    certs = build_demo_chain()
    certs["demo-proof-001"]["scope"] = {"resources": ["/admin"], "operations": ["GET"]}
    sim = IntentCertificateSimulator(certs)
    decision = sim.evaluate(request("demo-proof-001", "tamper-attack", resource="/admin"))
    scenarios.append({
        "id": "A2_CERTIFICATE_TAMPERING",
        "description": "Payload is modified without recomputing its signature.",
        "expected": "DENY",
        "observed": decision.outcome,
        "reason": decision.reason,
        "contained": decision.outcome == "DENY" and decision.reason == "INVALID_SIGNATURE",
    })

    # 3: certificate revocation.
    sim = IntentCertificateSimulator(build_demo_chain(), revoked={"demo-proof-001"})
    decision = sim.evaluate(request("demo-proof-001", "revoked-attack"))
    scenarios.append({
        "id": "A3_REVOKED_CERTIFICATE",
        "description": "A certificate already present in the local revocation set is used.",
        "expected": "DENY",
        "observed": decision.outcome,
        "reason": decision.reason,
        "contained": decision.outcome == "DENY" and decision.reason == "CERTIFICATE_REVOKED",
    })

    # 4: intent is syntactically valid but its real-world truth is not knowable here.
    sim = IntentCertificateSimulator(build_demo_chain())
    decision = sim.evaluate(request("demo-proof-001", "false-intent", intent="monitor_availability"))
    scenarios.append({
        "id": "A4_FALSE_BUT_MATCHING_INTENT",
        "description": "Client declares a permitted intent; simulator cannot know whether the human/business purpose is truthful.",
        "expected": "UNDETECTABLE_BY_DECLARATION_ALONE",
        "observed": decision.outcome,
        "reason": decision.reason,
        "contained": False,
        "finding": "The request is allowed if scope and rate are valid; intent string is not semantic proof.",
    })

    # 5: Sybil-like coordinated traffic across distinct valid certificates.
    all_certs: dict[str, dict[str, Any]] = {}
    demos: list[str] = []
    for n in range(20):
        chain = make_client_chain(n)
        all_certs.update(chain)
        demos.append(f"demo-{n:04d}")
    sim = IntentCertificateSimulator(all_certs)
    outcomes = Counter()
    for n, cert_id in enumerate(demos):
        for k in range(3):
            outcome = sim.evaluate(request(cert_id, f"sybil-{n}-{k}", second=k))
            outcomes[outcome.outcome] += 1
    total_allowed = outcomes.get("ALLOW", 0)
    scenarios.append({
        "id": "A5_DISTRIBUTED_MANY_CERTIFICATES",
        "description": "20 independently valid demo certificates each issue 3 in-scope requests in one minute.",
        "configured_limit": "3 requests/minute per certificate",
        "clients": 20,
        "requests": 60,
        "observed_outcomes": dict(sorted(outcomes.items())),
        "observed_allowed": total_allowed,
        "contained": total_allowed < 60,
        "finding": "Per-certificate quota is bypassed at aggregate service level: all 60 requests pass. No subject, account, service-wide, or cross-certificate budget exists.",
    })

    # 6: separate nodes each hold independent counters for the same certificate.
    shared_certs = build_demo_chain()
    node_a = IntentCertificateSimulator(shared_certs)
    node_b = IntentCertificateSimulator(shared_certs)
    node_outcomes = [
        node_a.evaluate(request("demo-proof-001", "node-a-1", second=0)).outcome,
        node_a.evaluate(request("demo-proof-001", "node-a-2", second=1)).outcome,
        node_a.evaluate(request("demo-proof-001", "node-a-3", second=2)).outcome,
        node_b.evaluate(request("demo-proof-001", "node-b-1", second=0)).outcome,
        node_b.evaluate(request("demo-proof-001", "node-b-2", second=1)).outcome,
        node_b.evaluate(request("demo-proof-001", "node-b-3", second=2)).outcome,
    ]
    allowed = node_outcomes.count("ALLOW")
    scenarios.append({
        "id": "A6_MULTI_NODE_COUNTER_SPLIT",
        "description": "Two independent enforcement nodes each receive 3 requests using the same certificate.",
        "configured_limit": "3 requests/minute per certificate, per local simulator instance",
        "requests": len(node_outcomes),
        "observed_outcomes": dict(sorted(Counter(node_outcomes).items())),
        "observed_allowed": allowed,
        "contained": allowed <= 3,
        "finding": "Six requests pass because rate counters are local. No distributed quota coordination is implemented.",
    })

    # 7: replay the same request ID repeatedly. Shows lack of replay nonce; rate limit is incidental mitigation.
    sim = IntentCertificateSimulator(build_demo_chain())
    replay = request("demo-proof-001", "identical-request-id-replayed")
    replay_results = [sim.evaluate(dict(replay)) for _ in range(5)]
    replay_allowed = sum(d.outcome == "ALLOW" for d in replay_results)
    scenarios.append({
        "id": "A7_REPLAY_SAME_REQUEST",
        "description": "The identical request ID and payload are submitted five times.",
        "requests": len(replay_results),
        "observed_outcomes": dict(sorted(Counter(d.outcome for d in replay_results).items())),
        "observed_allowed": replay_allowed,
        "contained": replay_allowed == 0,
        "finding": "There is no nonce, idempotency store, or replay cache. Three replays pass before the per-certificate rate limit happens to stop the rest.",
    })

    # 8: suspicion is local state; demonstrate one node restricts while a peer with no signal allows.
    certs = build_demo_chain()
    suspicious_node = IntentCertificateSimulator(certs, suspect={"demo-proof-001"})
    unaware_node = IntentCertificateSimulator(certs)
    a = suspicious_node.evaluate(request("demo-proof-001", "suspect-node", second=0))
    b = unaware_node.evaluate(request("demo-proof-001", "unaware-node", second=0))
    scenarios.append({
        "id": "A8_SUSPICION_NOT_PROPAGATED",
        "description": "Node A has local suspicion state; node B has not received any signed risk event.",
        "node_a": {"outcome": a.outcome, "reason": a.reason},
        "node_b": {"outcome": b.outcome, "reason": b.reason},
        "contained": False,
        "finding": "Risk-state propagation, signatures on risk events, freshness, issuer authorization, and consistency are not implemented.",
    })

    # 9: malformed request timestamp demonstrates input-hardening gap.
    sim = IntentCertificateSimulator(build_demo_chain())
    malformed = request("demo-proof-001", "malformed-time")
    malformed["timestamp"] = "not-a-time"
    try:
        sim.evaluate(malformed)
        malformed_result = "NO_EXCEPTION"
    except (ValueError, TypeError, KeyError):
        malformed_result = "UNHANDLED_INPUT_EXCEPTION"
    scenarios.append({
        "id": "A9_MALFORMED_REQUEST",
        "description": "Request has an invalid timestamp.",
        "observed": malformed_result,
        "contained": malformed_result == "NO_EXCEPTION",
        "finding": "Malformed input raises an exception rather than returning a controlled deny result; a production validator needs strict schema and exception handling.",
    })

    contained = sum(s.get("contained", False) for s in scenarios)
    return {
        "mode": "LOCAL_SYNTHETIC_ATTACK_SIMULATION",
        "target": "intent-certificate-prototype-only",
        "live_network_access": False,
        "scenario_count": len(scenarios),
        "scenarios_contained_by_current_prototype": contained,
        "scenarios_with_gaps": len(scenarios) - contained,
        "overall_result": "NOT_READY_FOR_COORDINATED_ATTACK_DEFENSE",
        "scenarios": scenarios,
        "limitations": [
            "No real packets, sockets, website, or third-party system were used.",
            "This is functional logic testing, not load testing or penetration testing.",
            "HMAC secret is public demo material and is not production cryptography.",
            "No network/transport DDoS protection is tested.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run_attack_simulation(), indent=2, sort_keys=True))
