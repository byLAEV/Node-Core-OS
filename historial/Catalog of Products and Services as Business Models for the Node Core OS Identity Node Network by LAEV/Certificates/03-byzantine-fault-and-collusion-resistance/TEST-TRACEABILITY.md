# Test Traceability — Byzantine Fault and Collusion Resistance

- **Product ID:** `CERT-03`
- **Profile identifier:** `byzantine-collusion-resistance`
- **Evidence classification:** **PARTIAL / INDIRECT**
- **Catalog status:** Proposed service
- **Economic policy:** `pending-consensus`

## Existing test sources

- [`tests/test_distributed_defense.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_distributed_defense.py)
- [`tests/test_shield_distributed_alert_acceptance.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_shield_distributed_alert_acceptance.py)
- [`tests/test_shield_identity_credential.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_shield_identity_credential.py)

## GitHub Actions workflows

- [`.github/workflows/certificate-adversarial-tests.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/certificate-adversarial-tests.yml)
- [`.github/workflows/shield-comparative-lab.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/shield-comparative-lab.yml)

## What the current evidence supports

Tests cover signed event validity, trust, expiry, tampering, quorum thresholds, repeated reports, replay, reporter revocation, and selected three-node loopback scenarios.

## What is not demonstrated

These are corroboration and alert-acceptance tests, not proof of a Byzantine consensus protocol, quorum safety/liveness under a stated fault threshold, or resistance to coordinated operators.

## Required next tests

Add protocol-level fault injection with explicit assumptions, conflicting proposals, quorum boundary tests, collusion scenarios, safety/liveness assertions, and recovery checks.

## Required evidence fields

For each future run record product/profile ID, authorization and scope, commit SHA, workflow/run ID and URL, test names, environment and dependency versions, expected and observed results, evidence hashes, reviewer, limitations, and remediation/retest status. A passing job supports only the assertions it executed.

## Certificate issuance rule

Do not market this profile as a successful security assessment solely because the certificate format accepts its identifier. Product approval requires published acceptance criteria and reviewed evidence. A signature proves key-based origin and message integrity, not the independent truth of every claim.

## Related references

- [Catalog-wide audit and CI index](../AUDIT-AND-CI-INDEX.md)
- [Certificate test/evidence matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)
- [Spanish technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.md)
- [English technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.en.md)
