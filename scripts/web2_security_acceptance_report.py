#!/usr/bin/env python3
"""Run isolated Node Core OS Web2 security tests and emit reproducible evidence."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import unittest

PATTERNS = (
    "test_certificate_web_lab.py",
    "test_shield_web_attack_lab.py",
    "test_api_abuse_lab.py",
    "test_standard_https_validation.py",
    "test_web_tls_profile.py",
    "test_distributed_defense.py",
    "test_p2p_tls_transport.py",
)

class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self.started = {}

    def startTest(self, test):
        self.started[test.id()] = time.monotonic()
        super().startTest(test)

    def record(self, test, status, detail=""):
        elapsed = time.monotonic() - self.started.get(test.id(), time.monotonic())
        self.records.append({
            "test": test.id(),
            "status": status,
            "duration_seconds": round(max(0.0, elapsed), 6),
            "detail": detail,
        })

    def addSuccess(self, test):
        self.record(test, "PASS")
        super().addSuccess(test)

    def addFailure(self, test, err):
        self.record(test, "FAIL", self._exc_info_to_string(err, test)[-2000:])
        super().addFailure(test, err)

    def addError(self, test, err):
        self.record(test, "ERROR", self._exc_info_to_string(err, test)[-2000:])
        super().addError(test, err)

    def addSkip(self, test, reason):
        self.record(test, "SKIPPED", str(reason))
        super().addSkip(test, reason)

class EvidenceRunner(unittest.TextTestRunner):
    resultclass = EvidenceResult

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="artifacts/web2-security-report")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    missing = []
    for pattern in PATTERNS:
        found = loader.discover("tests", pattern=pattern)
        if found.countTestCases() == 0:
            missing.append(pattern)
        suite.addTests(found)

    started = time.monotonic()
    result = EvidenceRunner(verbosity=2).run(suite)
    duration = round(time.monotonic() - started, 3)
    statuses = ("PASS", "FAIL", "ERROR", "SKIPPED")
    counts = {name: sum(r["status"] == name for r in result.records) for name in statuses}
    passed = result.wasSuccessful() and not missing

    report = {
        "schema_version": 1,
        "report": "Node Core OS byLAEV - Web2 isolated security acceptance",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "target": "synthetic loopback services only",
            "external_hosts_contacted": False,
            "production_credentials_used": False,
            "transport_profiles": [
                "Node Core OS pinned-certificate mutual TLS (TLS 1.3)",
                "standard HTTPS CA-chain and hostname validation"
            ]
        },
        "summary": {
            "result": "PASS" if passed else "FAIL",
            "tests_run": result.testsRun,
            "duration_seconds": duration,
            "counts": counts,
            "missing_test_patterns": missing
        },
        "observed_controls": {
            "authorized_identity_access": "TESTED",
            "untrusted_client_certificate_rejection": "TESTED",
            "impostor_server_certificate_rejection": "TESTED",
            "standard_https_hostname_and_ca_validation": "TESTED",
            "malformed_and_oversized_api_payload_rejection": "TESTED",
            "bounded_request_rate_limit": "TESTED",
            "signed_report_quorum_and_tamper_rejection": "TESTED",
            "two_report_non_quarantine_case": "TESTED; one deterministic case, not a statistical false-positive rate",
            "distributed_event_partition_and_recovery_primitives": "Only as covered by selected existing tests"
        },
        "not_demonstrated": {
            "production_web_application_recovery": "NOT_IMPLEMENTED_IN_THIS_LAB",
            "statistical_false_positive_rate": "NOT_MEASURED",
            "volumetric_ddos_resistance": "NOT_TESTED",
            "browser_trust_store_or_public_web_pki_deployment": "NOT_TESTED",
            "production_kubo_ipfs_or_internet_p2p_convergence": "NOT_TESTED",
            "eight_proposed_profiles_as_deployable_web_server_certificates": "NOT_ESTABLISHED"
        },
        "tests": sorted(result.records, key=lambda item: item["test"])
    }

    json_path = output_dir / "web2-security-report.json"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Node Core OS byLAEV - Web2 security acceptance report",
        "",
        "- Generated UTC: " + report["generated_at_utc"],
        "- Result: **" + report["summary"]["result"] + "**",
        "- Tests run: **" + str(result.testsRun) + "**",
        "- Duration: **" + str(duration) + " seconds**",
        "- Scope: synthetic identities and loopback services; no external targets.",
        "",
        "## Test counts",
        "",
        "| Result | Count |",
        "|---|---:|"
    ]
    lines.extend("| " + key + " | " + str(value) + " |" for key, value in counts.items())
    lines.extend(["", "## Control coverage", ""])
    lines.extend("- **" + key + "**: " + value for key, value in report["observed_controls"].items())
    lines.extend(["", "## Explicit limitations", ""])
    lines.extend("- **" + key + "**: " + value for key, value in report["not_demonstrated"].items())
    lines.extend(["", "## Individual test results", "", "| Status | Test | Duration (s) |", "|---|---|---:|"])
    lines.extend(
        "| " + item["status"] + " | " + item["test"] + " | " +
        format(item["duration_seconds"], ".6f") + " |"
        for item in report["tests"]
    )
    if missing:
        lines.extend(["", "## Missing test modules", ""])
        lines.extend("- " + item for item in missing)
    lines.extend([
        "",
        "> A passing report establishes only the assertions listed above in this CI environment. It is not a production security certification.",
        ""
    ])
    (output_dir / "web2-security-report.md").write_text("\n".join(lines), encoding="utf-8")
    print("JSON report: " + str(json_path))
    print("Markdown report: " + str(output_dir / "web2-security-report.md"))
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
