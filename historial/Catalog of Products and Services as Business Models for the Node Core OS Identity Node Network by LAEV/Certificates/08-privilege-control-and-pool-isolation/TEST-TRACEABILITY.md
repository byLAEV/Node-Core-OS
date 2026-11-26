# Test Traceability — Privilege Control and Pool Isolation

- **Product ID:** `CERT-08`
- **Profile identifier:** `privilege-and-pool-isolation`
- **Evidence classification:** **PROFILE ONLY / NO DEDICATED EFFECTIVENESS TEST**
- **Catalog status:** Proposed service
- **Economic policy:** `pending-consensus`

## Existing test sources

- [`tests/test_node_identity_certificate.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_node_identity_certificate.py)

## GitHub Actions workflows

- [`.github/workflows/node-identity-certificate.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/node-identity-certificate.yml)

## What the current evidence supports

The profile identifier is accepted by the certificate implementation and generic certificate-envelope tests exercise profile allowlisting.

## What is not demonstrated

No mapped product-specific test suite establishes application authorization, cross-tenant/pool isolation, least privilege, or privilege-escalation resistance for this profile.

## Required next tests

Add actor/resource/action authorization matrix tests, cross-pool negative access, least privilege, privilege escalation, and administrative/recovery boundary tests.

## Required evidence fields

For each future run record product/profile ID, authorization and scope, commit SHA, workflow/run ID and URL, test names, environment and dependency versions, expected and observed results, evidence hashes, reviewer, limitations, and remediation/retest status. A passing job supports only the assertions it executed.

## Certificate issuance rule

Do not market this profile as a successful security assessment solely because the certificate format accepts its identifier. Product approval requires published acceptance criteria and reviewed evidence. A signature proves key-based origin and message integrity, not the independent truth of every claim.

## Related references

- [Catalog-wide audit and CI index](../AUDIT-AND-CI-INDEX.md)
- [Certificate test/evidence matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)
- [Spanish technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.md)
- [English technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.en.md)
