#!/usr/bin/env python3
"""Validate eight-certificate catalog completeness, not security effectiveness."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / (
    "Catalog of Products and Services as Business Models for the "
    "Node Core OS Identity Node Network by LAEV"
)
CERTIFICATES = CATALOG / "Certificates"
IMPLEMENTATION = ROOT / "node_core/security/node_identity_certificate.py"
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
    print("- This is a documentation consistency check, not a security effectiveness test")
    return 0


if __name__ == "__main__":
    sys.exit(main())
