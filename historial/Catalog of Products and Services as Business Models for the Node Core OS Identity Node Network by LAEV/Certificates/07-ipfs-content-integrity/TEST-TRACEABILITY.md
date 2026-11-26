# Test Traceability — IPFS Content Integrity

- **Product ID:** `CERT-07`
- **Profile identifier:** `ipfs-content-integrity`
- **Evidence classification:** **PROFILE ONLY / NEEDS EVIDENCE MAPPING**
- **Catalog status:** Proposed service
- **Economic policy:** `pending-consensus`

## Existing test sources

- [`tests/test_node_identity_certificate.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_node_identity_certificate.py)

## GitHub Actions workflows

- [`.github/workflows/node-identity-certificate.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/node-identity-certificate.yml)

## What the current evidence supports

The profile identifier is accepted by the certificate implementation. Separate Kubo/IPFS workflows exist, but their results are not automatically evidence for this product unless assertions directly test the advertised content-integrity claims.

## What is not demonstrated

No mapped product-specific evidence currently establishes CID/content mismatch handling, retrieval integrity, pinning/retention claims, or malicious-content handling for this profile.

## Required next tests

Map the Kubo workflow and tests by exact assertion; add correct/mismatched CID fixtures, missing-block and retrieval failures, pin/retention tests, and safe untrusted-content handling.

## Required evidence fields

For each future run record product/profile ID, authorization and scope, commit SHA, workflow/run ID and URL, test names, environment and dependency versions, expected and observed results, evidence hashes, reviewer, limitations, and remediation/retest status. A passing job supports only the assertions it executed.

## Certificate issuance rule

Do not market this profile as a successful security assessment solely because the certificate format accepts its identifier. Product approval requires published acceptance criteria and reviewed evidence. A signature proves key-based origin and message integrity, not the independent truth of every claim.

## Related references

- [Catalog-wide audit and CI index](../AUDIT-AND-CI-INDEX.md)
- [Certificate test/evidence matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)
- [Spanish technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.md)
- [English technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.en.md)
