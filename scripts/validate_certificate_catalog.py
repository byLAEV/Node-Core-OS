#!/usr/bin/env python3
"""Validate eight-certificate catalog completeness, not security effectiveness."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / (
    "Catalog of Products and Services as Business Models for the "
    "Node Core OS Identity Node Network by LAEV"
)
CERTIFICATES = CATALOG / "Certificates"
IMPLEMENTATION = ROOT / "node_core/security/node_identity_certificate.py"
LOBBY_CATALOG = ROOT / "compatibility/termux/lobby/certificates/catalog.json"
PRODUCTS = {
    "01-sybil-and-fake-node-resistance": "sybil-resistance",
    "02-p2p-partition-and-eclipse-resistance": "p2p-partition-eclipse-resistance",
    "03-byzantine-fault-and-collusion-resistance": "byzantine-collusion-resistance",
    "04-identity-authenticity-and-key-protection": "identity-key-protection",
    "05-software-supply-chain-integrity": "software-supply-chain-integrity",
    "06-availability-and-ddos-resilience": "availability-ddos-resistance",
    "07-ipfs-content-integrity": "ipfs-content-integrity",
    "08-privilege-control-and-pool-isolation": "privilege-and-pool-isolation",
}
SHARED = (
    "README.md",
    "BUSINESS-MODEL-AND-CONSENSUS.md",
    "CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md",
    "AUDIT-AND-CI-INDEX.md",
)
PRODUCT_FILES = (
    "README.md",
    "SERVICE-SPECIFICATION.md",
    "EVIDENCE-AND-TESTING.md",
    "TEST-TRACEABILITY.md",
)


def main() -> int:
    errors: list[str] = []
    if not CATALOG.is_dir() or not CERTIFICATES.is_dir() or not IMPLEMENTATION.is_file():
        print("ERROR: catalog directory, Certificates directory, or certificate implementation is missing")
        return 1
    if not LOBBY_CATALOG.is_file() or LOBBY_CATALOG.is_symlink():
        print("ERROR: Lobby security certificate catalog is missing or unsafe")
        return 1
    try:
        lobby_catalog = json.loads(LOBBY_CATALOG.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: Lobby security certificate catalog is unreadable: {exc}")
        return 1
    if not isinstance(lobby_catalog, dict) or lobby_catalog.get("schema_version") != 1:
        print("ERROR: unsupported Lobby security certificate catalog schema")
        return 1
    lobby_profiles = lobby_catalog.get("security_profiles")
    if not isinstance(lobby_profiles, list):
        print("ERROR: Lobby security profiles must be a list")
        return 1
    lobby_profile_ids = [
        item.get("id") for item in lobby_profiles if isinstance(item, dict)
    ]
    if len(lobby_profile_ids) != len(lobby_profiles) or set(lobby_profile_ids) != set(PRODUCTS.values()) or len(lobby_profile_ids) != len(set(lobby_profile_ids)):
        errors.append("Lobby security profile IDs do not exactly match the canonical eight-profile catalog")
    if any(item.get("installable_certificate") is not False for item in lobby_profiles if isinstance(item, dict)):
        errors.append("security evaluation profiles must not be marked as installable X.509 certificates")
    technical = lobby_catalog.get("technical_certificates")
    if not isinstance(technical, list):
        errors.append("Lobby technical_certificates must be a list")
    elif any(not isinstance(item, dict) or not isinstance(item.get("id"), str) for item in technical):
        errors.append("Lobby technical certificate entries must have unique string IDs")
    elif len({item["id"] for item in technical}) != len(technical):
        errors.append("Lobby technical certificate IDs must be unique")

    for name in SHARED:
        if not (CATALOG / name).is_file():
            errors.append(f"missing shared catalog file: {name}")

    implementation = IMPLEMENTATION.read_text(encoding="utf-8")
    index_path = CATALOG / "README.md"
    index = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""

    for folder, profile in PRODUCTS.items():
        if f'"{profile}"' not in implementation:
            errors.append(f"profile missing from implementation allowlist: {profile}")
        if f"`{profile}`" not in index:
            errors.append(f"profile missing from catalog README: {profile}")
        product_dir = CERTIFICATES / folder
        if not product_dir.is_dir():
            errors.append(f"missing product directory: Certificates/{folder}")
            continue
        for name in PRODUCT_FILES:
            path = product_dir / name
            if not path.is_file():
                errors.append(f"missing product file: Certificates/{folder}/{name}")
                continue
            content = path.read_text(encoding="utf-8")
            if profile not in content:
                errors.append(f"profile {profile} missing from Certificates/{folder}/{name}")
        readme_path = product_dir / "README.md"
        if readme_path.is_file():
            readme = readme_path.read_text(encoding="utf-8")
            for linked in ("SERVICE-SPECIFICATION.md", "EVIDENCE-AND-TESTING.md", "TEST-TRACEABILITY.md"):
                if linked not in readme:
                    errors.append(f"Certificates/{folder}/README.md missing link to {linked}")

    if errors:
        print("Certificate catalog integrity: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Certificate catalog integrity: PASS")
    print(f"- {len(PRODUCTS)} profiles align with the implementation and catalog index")
    print(f"- {len(PRODUCTS) * len(PRODUCT_FILES)} per-product documentation files exist under Certificates/")
    print(f"- {len(SHARED)} shared catalog documents exist")
    print("- Lobby technical certificate inventory and eight security profiles match the canonical product catalog")
    print("- This is a documentation consistency check, not a security effectiveness test")
    return 0


if __name__ == "__main__":
    sys.exit(main())
