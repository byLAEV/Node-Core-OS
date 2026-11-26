# Test Traceability — Availability and DDoS Resilience

- **Product ID:** `CERT-06`
- **Profile identifier:** `availability-ddos-resistance`
- **Evidence classification:** **PARTIAL / BOUNDED API LAB ONLY**
- **Catalog status:** Proposed service
- **Economic policy:** `pending-consensus`

## Existing test sources

- [`tests/test_api_abuse_lab.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_api_abuse_lab.py)
- [`tests/test_node_identity_certificate.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_node_identity_certificate.py)

## GitHub Actions workflows

- [`.github/workflows/certificate-adversarial-tests.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/certificate-adversarial-tests.yml)
- [`.github/workflows/web2-security-acceptance-report.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/web2-security-acceptance-report.yml)
- [`.github/workflows/shield-comparative-lab.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/shield-comparative-lab.yml)

## What the current evidence supports

The Web2 acceptance suite includes malformed/oversized request and bounded rate-limit scenarios in a synthetic loopback handler. The report explicitly excludes volumetric DDoS and production availability.

## What is not demonstrated

No volumetric DDoS, internet-scale capacity, production service resilience, or broad resource-exhaustion protection is established. Do not run volumetric tests on shared GitHub runners.

## Required next tests

Add bounded isolated resource-exhaustion and recovery tests, rate-limit assertions, latency/error/resource metrics, and documented abort thresholds; do not run uncontrolled public DDoS.

## Required evidence fields

For each future run record product/profile ID, authorization and scope, commit SHA, workflow/run ID and URL, test names, environment and dependency versions, expected and observed results, evidence hashes, reviewer, limitations, and remediation/retest status. A passing job supports only the assertions it executed.

## Certificate issuance rule

Do not market this profile as a successful security assessment solely because the certificate format accepts its identifier. Product approval requires published acceptance criteria and reviewed evidence. A signature proves key-based origin and message integrity, not the independent truth of every claim.

## Related references

- [Catalog-wide audit and CI index](../AUDIT-AND-CI-INDEX.md)
- [Certificate test/evidence matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)
- [Spanish technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.md)
- [English technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.en.md)
