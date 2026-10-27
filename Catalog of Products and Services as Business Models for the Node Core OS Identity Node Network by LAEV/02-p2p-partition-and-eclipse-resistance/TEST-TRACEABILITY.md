# Test Traceability — P2P Partition and Eclipse Resistance

- **Product ID:** `CERT-02`
- **Profile identifier:** `p2p-partition-eclipse-resistance`
- **Evidence classification:** **PARTIAL / INDIRECT**
- **Catalog status:** Proposed service
- **Economic policy:** `pending-consensus`

## Existing test sources

- [`tests/test_p2p_tls_transport.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_p2p_tls_transport.py)
- [`tests/test_shield_distributed_alert_acceptance.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_shield_distributed_alert_acceptance.py)
- [`tests/test_p2p_status_request_response.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_p2p_status_request_response.py)
- [`tests/test_p2p_peer_service.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_p2p_peer_service.py)

## GitHub Actions workflows

- [`.github/workflows/certificate-adversarial-tests.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/certificate-adversarial-tests.yml)
- [`.github/workflows/shield-comparative-lab.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/shield-comparative-lab.yml)

## What the current evidence supports

TLS peer identity/pinning and a controlled three-node A-to-B-to-C loopback alert test cover selected peer authentication and partition/recovery behavior.

## What is not demonstrated

No complete eclipse attack, malicious peer selection, peer poisoning, topology diversity, or broad partition/recovery campaign is established by these tests.

## Required next tests

Add bounded peer-poisoning and eclipse simulations, peer diversity assertions, stale-peer tests, partition duration scenarios, and recovery invariants.

## Required evidence fields

For each future run record product/profile ID, authorization and scope, commit SHA, workflow/run ID and URL, test names, environment and dependency versions, expected and observed results, evidence hashes, reviewer, limitations, and remediation/retest status. A passing job supports only the assertions it executed.

## Certificate issuance rule

Do not market this profile as a successful security assessment solely because the certificate format accepts its identifier. Product approval requires published acceptance criteria and reviewed evidence. A signature proves key-based origin and message integrity, not the independent truth of every claim.

## Related references

- [Catalog-wide audit and CI index](../AUDIT-AND-CI-INDEX.md)
- [Certificate test/evidence matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)
- [Spanish technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.md)
- [English technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.en.md)
