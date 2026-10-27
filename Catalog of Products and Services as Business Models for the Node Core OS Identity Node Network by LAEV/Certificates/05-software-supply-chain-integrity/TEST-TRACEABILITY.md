# Test Traceability — Software Supply-Chain Integrity

- **Product ID:** `CERT-05`
- **Profile identifier:** `software-supply-chain-integrity`
- **Evidence classification:** **PROFILE ONLY / NO DEDICATED EFFECTIVENESS TEST**
- **Catalog status:** Proposed service
- **Economic policy:** `pending-consensus`

## Existing test sources

- [`tests/test_node_identity_certificate.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_node_identity_certificate.py)

## GitHub Actions workflows

- [`.github/workflows/node-identity-certificate.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/node-identity-certificate.yml)
- [`.github/workflows/certificate-adversarial-tests.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/certificate-adversarial-tests.yml)

## What the current evidence supports

The profile identifier is accepted by the certificate implementation. Generic certificate-envelope tests exercise credential validation; dependency installation in CI is not itself a supply-chain security assessment.

## What is not demonstrated

No product-specific evidence establishes artifact provenance, dependency tamper detection, reproducible builds, signed update verification, or rollback protection for this profile.

## Required next tests

Add artifact signature/provenance checks, dependency tampering fixtures, reproducible-build comparison, update signature validation, and rollback rejection.

## Required evidence fields

For each future run record product/profile ID, authorization and scope, commit SHA, workflow/run ID and URL, test names, environment and dependency versions, expected and observed results, evidence hashes, reviewer, limitations, and remediation/retest status. A passing job supports only the assertions it executed.

## Certificate issuance rule

Do not market this profile as a successful security assessment solely because the certificate format accepts its identifier. Product approval requires published acceptance criteria and reviewed evidence. A signature proves key-based origin and message integrity, not the independent truth of every claim.

## Related references

- [Catalog-wide audit and CI index](../AUDIT-AND-CI-INDEX.md)
- [Certificate test/evidence matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)
- [Spanish technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.md)
- [English technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.en.md)
