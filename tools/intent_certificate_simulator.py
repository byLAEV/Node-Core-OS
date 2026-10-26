#!/usr/bin/env python3
"""Educational Node Core OS intent-certificate simulator. Python 3.10+, stdlib only.

HMAC uses a synthetic shared demo secret. This is simulation-only, not production PKI.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import hmac
import json
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

DEMO_SECRET = b"NODE-CORE-OS-INTENT-CERT-DEMO-ONLY-NOT-FOR-PRODUCTION"
SCHEMA_VERSION = "1.0"


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def signed_certificate(**fields: Any) -> dict[str, Any]:
    certificate = {"schema_version": SCHEMA_VERSION, **fields}
    unsigned = {key: value for key, value in certificate.items() if key != "signature"}
    certificate["signature"] = hmac.new(DEMO_SECRET, canonical_bytes(unsigned), hashlib.sha256).hexdigest()
    return certificate


def signature_valid(certificate: dict[str, Any]) -> bool:
    supplied = certificate.get("signature")
    if not isinstance(supplied, str):
        return False
    unsigned = {key: value for key, value in certificate.items() if key != "signature"}
    expected = hmac.new(DEMO_SECRET, canonical_bytes(unsigned), hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied, expected)


def scope_contains(scope: dict[str, Any], resource: str, operation: str) -> bool:
    return operation in scope.get("operations", []) and any(
        isinstance(pattern, str) and fnmatch.fnmatchcase(resource, pattern)
        for pattern in scope.get("resources", [])
    )


def scope_is_subset(child: dict[str, Any], parent: dict[str, Any]) -> bool:
    # Conservative: this prototype accepts only literal inherited patterns.
    return (set(child.get("resources", [])).issubset(set(parent.get("resources", []))
            ) and set(child.get("operations", [])).issubset(set(parent.get("operations", []))))


@dataclass
class Decision:
    request_id: str
    outcome: str
    reason: str
    certificate_id: str
    intent: str
    resource: str
    operation: str
    timestamp: str


class IntentCertificateSimulator:
    def __init__(self, certificates: dict[str, dict[str, Any]], *,
                 revoked: set[str] | None = None, suspect: set[str] | None = None) -> None:
        self.certificates = certificates
        self.revoked = revoked or set()
        self.suspect = suspect or set()
        self.request_times: dict[str, deque[datetime]] = defaultdict(deque)
        self.events: list[Decision] = []

    def _chain(self, leaf_id: str, now: datetime) -> tuple[list[dict[str, Any]], str | None]:
        chain: list[dict[str, Any]] = []
        current_id = leaf_id
        seen: set[str] = set()
        while current_id:
            if current_id in seen:
                return [], "CERTIFICATE_CHAIN_CYCLE"
            seen.add(current_id)
            cert = self.certificates.get(current_id)
            if cert is None:
                return [], "CERTIFICATE_NOT_FOUND"
            if not signature_valid(cert):
                return [], "INVALID_SIGNATURE"
            if cert.get("schema_version") != SCHEMA_VERSION:
                return [], "UNSUPPORTED_SCHEMA_VERSION"
            if current_id in self.revoked or cert.get("status") == "revoked":
                return [], "CERTIFICATE_REVOKED"
            try:
                issued, expires = parse_time(cert["issued_at"]), parse_time(cert["expires_at"])
            except (KeyError, TypeError, ValueError):
                return [], "INVALID_CERTIFICATE_TIME"
            if now < issued:
                return [], "CERTIFICATE_NOT_YET_VALID"
            if now >= expires:
                return [], "CERTIFICATE_EXPIRED"
            chain.append(cert)
            parent_id = cert.get("parent_certificate_id")
            if not parent_id:
                break
            current_id = parent_id
        chain.reverse()
        if [c.get("certificate_type") for c in chain] != ["general", "specific", "demonstration"]:
            return [], "INVALID_CERTIFICATE_CHAIN"
        for parent, child in zip(chain, chain[1:]):
            if child.get("parent_certificate_id") != parent.get("certificate_id"):
                return [], "INVALID_CERTIFICATE_PARENT"
            if not scope_is_subset(child.get("scope", {}), parent.get("scope", {})):
                return [], "CHILD_SCOPE_EXCEEDS_PARENT"
        return chain, None

    def evaluate(self, request: dict[str, Any]) -> Decision:
        now = parse_time(request["timestamp"])
        cert_id = str(request.get("certificate_id", ""))
        resource = str(request.get("resource", ""))
        operation = str(request.get("operation", "")).upper()
        intent = str(request.get("intent", ""))
        request_id = str(request.get("request_id", "missing-request-id"))

        def finish(outcome: str, reason: str) -> Decision:
            event = Decision(request_id, outcome, reason, cert_id, intent, resource,
                             operation, now.isoformat().replace("+00:00", "Z"))
            self.events.append(event)
            return event

        chain, error = self._chain(cert_id, now)
        if error:
            return finish("DENY", error)
        demonstration = chain[-1]
        if not intent or intent != demonstration.get("intent"):
            return finish("DENY", "INTENT_MISMATCH")
        proof = demonstration.get("demonstration", {})
        if not isinstance(proof, dict) or len(str(proof.get("justification", "")).strip()) < 12:
            return finish("DENY", "DEMONSTRATION_INSUFFICIENT")
        if any(not scope_contains(c.get("scope", {}), resource, operation) for c in chain):
            return finish("DENY", "REQUEST_OUTSIDE_CERTIFICATE_SCOPE")

        # Suspicion is reversible: read-only and one request/minute, not revocation.
        if cert_id in self.suspect:
            if operation != "GET":
                return finish("LIMIT", "SUSPECT_CERTIFICATE_READ_ONLY")
            if self._rate_limited(cert_id, now, 1):
                return finish("LIMIT", "SUSPECT_CERTIFICATE_RATE_LIMIT")
            self._record_request(cert_id, now)
            return finish("ALLOW_RESTRICTED", "SUSPECT_CERTIFICATE_RESTRICTED")

        maximum = int(demonstration.get("limits", {}).get("requests_per_minute", 0))
        if maximum < 1:
            return finish("DENY", "INVALID_REQUEST_LIMIT")
        if self._rate_limited(cert_id, now, maximum):
            return finish("LIMIT", "REQUEST_RATE_LIMIT_EXCEEDED")
        self._record_request(cert_id, now)
        return finish("ALLOW", "INTENT_SCOPE_AND_CHAIN_VALID")

    def _rate_limited(self, cert_id: str, now: datetime, maximum: int) -> bool:
        events = self.request_times[cert_id]
        cutoff = now.timestamp() - 60
        while events and events[0].timestamp() <= cutoff:
            events.popleft()
        return len(events) >= maximum

    def _record_request(self, cert_id: str, now: datetime) -> None:
        self.request_times[cert_id].append(now)

    def metrics(self) -> dict[str, Any]:
        counts: dict[str, int] = defaultdict(int)
        reasons: dict[str, int] = defaultdict(int)
        for event in self.events:
            counts[event.outcome] += 1
            reasons[event.reason] += 1
        total = len(self.events)
        return {
            "total_requests": total,
            "outcomes": dict(sorted(counts.items())),
            "reasons": dict(sorted(reasons.items())),
            "allow_rate_percent": round(100 * counts.get("ALLOW", 0) / total, 2) if total else 0.0,
            "restricted_allow_count": counts.get("ALLOW_RESTRICTED", 0),
            "note": "Simulation metrics only; not production telemetry or proof of attack prevention.",
        }


def build_demo_chain() -> dict[str, dict[str, Any]]:
    general = signed_certificate(
        certificate_id="demo-general-001", certificate_type="general",
        issuer="node-core-demo-policy", subject="synthetic-monitor-bot",
        intent="monitor_availability", parent_certificate_id=None,
        scope={"resources": ["/status"], "operations": ["GET"]},
        issued_at="2026-01-01T00:00:00Z", expires_at="2027-01-01T00:00:00Z", status="active")
    specific = signed_certificate(
        certificate_id="demo-specific-001", certificate_type="specific",
        issuer="node-core-demo-policy", subject="synthetic-monitor-bot",
        intent="monitor_availability", parent_certificate_id="demo-general-001",
        scope={"resources": ["/status"], "operations": ["GET"]},
        issued_at="2026-01-01T00:00:00Z", expires_at="2026-12-01T00:00:00Z", status="active")
    demonstration = signed_certificate(
        certificate_id="demo-proof-001", certificate_type="demonstration",
        issuer="node-core-demo-policy", subject="synthetic-monitor-bot",
        intent="monitor_availability", parent_certificate_id="demo-specific-001",
        scope={"resources": ["/status"], "operations": ["GET"]},
        demonstration={"purpose": "Check public service availability",
                       "justification": "A status endpoint is required to measure service availability.",
                       "request_id": "demo-request-family-001"},
        limits={"requests_per_minute": 3},
        issued_at="2026-01-01T00:00:00Z", expires_at="2026-11-01T00:00:00Z", status="active")
    return {c["certificate_id"]: c for c in (general, specific, demonstration)}


def demo_requests() -> list[dict[str, Any]]:
    base = "2026-10-25T12:00:{:02d}Z"
    return [
        {"request_id": "req-001", "certificate_id": "demo-proof-001", "intent": "monitor_availability", "resource": "/status", "operation": "GET", "timestamp": base.format(0)},
        {"request_id": "req-002", "certificate_id": "demo-proof-001", "intent": "monitor_availability", "resource": "/status", "operation": "GET", "timestamp": base.format(5)},
        {"request_id": "req-003", "certificate_id": "demo-proof-001", "intent": "monitor_availability", "resource": "/admin", "operation": "GET", "timestamp": base.format(10)},
        {"request_id": "req-004", "certificate_id": "demo-proof-001", "intent": "monitor_availability", "resource": "/status", "operation": "POST", "timestamp": base.format(15)},
        {"request_id": "req-005", "certificate_id": "demo-proof-001", "intent": "monitor_availability", "resource": "/status", "operation": "GET", "timestamp": base.format(20)},
        {"request_id": "req-006", "certificate_id": "demo-proof-001", "intent": "monitor_availability", "resource": "/status", "operation": "GET", "timestamp": base.format(25)},
    ]


def run_demo() -> dict[str, Any]:
    simulator = IntentCertificateSimulator(build_demo_chain())
    decisions = [asdict(simulator.evaluate(request)) for request in demo_requests()]
    return {"mode": "SIMULATION_ONLY", "decisions": decisions, "metrics": simulator.metrics()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run deterministic synthetic scenarios")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    args = parser.parse_args(argv)
    if not args.demo:
        parser.error("choose --demo; this prototype intentionally does not accept live traffic")
    print(json.dumps(run_demo(), indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
