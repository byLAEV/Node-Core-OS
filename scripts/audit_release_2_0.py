#!/usr/bin/env python3
"""Validate the explicit Node Core OS 2.0 release evidence contract."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXPECTED_REQUIREMENTS = {
    "lobby_bootstrap_linux",
    "lobby_bootstrap_termux",
    "loopback_service_127_0_0_1_8765",
    "desktop_and_mobile_launchers",
    "read_only_preflight_and_consent",
    "linux_dependency_preparation",
    "official_package_signature_and_digest_verification",
    "core_installation_with_kubo",
    "core_certificate_installation_and_trust_validation",
    "open_node_core_from_lobby",
    "node_status_repair_maintenance",
    "update_preserves_identity_storage_ipfs_certificates",
    "ubuntu_debian_fedora_e2e",
    "termux_physical_device_acceptance",
    "all_required_prs_merged",
    "main_required_checks_green",
    "release_assets_and_checksums_verified",
}


def load_contract(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read readiness contract: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported readiness contract schema")
    if data.get("release") != "2.0.0":
        raise ValueError("Readiness contract must target release 2.0.0")
    requirements = data.get("requirements")
    if not isinstance(requirements, dict):
        raise ValueError("requirements must be a JSON object")
    actual = set(requirements)
    if actual != EXPECTED_REQUIREMENTS:
        missing = sorted(EXPECTED_REQUIREMENTS - actual)
        extra = sorted(actual - EXPECTED_REQUIREMENTS)
        raise ValueError(f"Requirement keys mismatch; missing={missing}, extra={extra}")
    if any(type(value) is not bool for value in requirements.values()):
        raise ValueError("Every requirement must be an explicit boolean")
    evidence = data.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a JSON object")
    for key in ("acceptance_report", "termux_device_report", "release_artifact_manifest", "sbom"):
        if not isinstance(evidence.get(key), str):
            raise ValueError(f"evidence.{key} must be a string")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness", required=True, type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--strict", default="false", choices=("true", "false"))
    args = parser.parse_args()

    try:
        data = load_contract(args.readiness)
    except ValueError as exc:
        print(f"READINESS CONTRACT ERROR: {exc}", file=sys.stderr)
        return 2

    requirements = data["requirements"]
    passed = sorted(key for key, value in requirements.items() if value)
    pending = sorted(key for key, value in requirements.items() if not value)
    lines = [
        "# Node Core OS 2.0 release readiness",
        "",
        f"- Release target: `v{data['release']}`",
        f"- Acceptance requirements evidenced: **{len(passed)}/{len(requirements)}**",
        f"- Pending requirements: **{len(pending)}**",
        "",
        "## Passed evidence",
        *(f"- [x] {key}" for key in passed),
        "",
        "## Pending blockers",
        *(f"- [ ] {key}" for key in pending),
        "",
    ]
    report = "\n".join(lines)
    print(report)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(report, encoding="utf-8")
    if args.strict == "true" and pending:
        print(f"STRICT RELEASE GATE BLOCKED: {len(pending)} acceptance requirements remain.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
