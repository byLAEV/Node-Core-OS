# Test Traceability — Identity Authenticity and Key Protection

- **Product ID:** `CERT-04`
- **Profile identifier:** `identity-key-protection`
- **Evidence classification:** **DIRECT FOR ENVELOPE; PARTIAL FOR OPERATIONAL SECURITY**
- **Catalog status:** Proposed service
- **Economic policy:** `pending-consensus`

## Existing test sources

- [`tests/test_node_identity_certificate.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_node_identity_certificate.py)
- [`tests/test_certificate_security.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_certificate_security.py)
- [`tests/test_p2p_tls_transport.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_p2p_tls_transport.py)
- [`tests/test_identity_associations.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_identity_associations.py)
- [`tests/test_identity_function.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_identity_function.py)
- [`tests/test_shield_identity_credential.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_shield_identity_credential.py)

## GitHub Actions workflows

- [`.github/workflows/node-identity-certificate.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/node-identity-certificate.yml)
- [`.github/workflows/certificate-adversarial-tests.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/certificate-adversarial-tests.yml)

## What the current evidence supports

Certificate-envelope tests cover issue/verify, tampering, unknown issuer, supplied revocation state, expiry/lifetime and profile validation; related suites cover node-key binding, TLS peer identity, and signed identity credentials.

## What is not demonstrated

This is not a complete key-custody audit. Issuer governance, key compromise response, key rotation/recovery, identity proofing, and reliable distributed revocation remain separate concerns.

## Required next tests

Add issuer-key/issuer-ID binding tests, rotation and recovery, unauthorized signing, permissions/custody, compromised-key revocation propagation, and restart anti-rollback tests.

## Required evidence fields

For each future run record product/profile ID, authorization and scope, commit SHA, workflow/run ID and URL, test names, environment and dependency versions, expected and observed results, evidence hashes, reviewer, limitations, and remediation/retest status. A passing job supports only the assertions it executed.

## Certificate issuance rule

Do not market this profile as a successful security assessment solely because the certificate format accepts its identifier. Product approval requires published acceptance criteria and reviewed evidence. A signature proves key-based origin and message integrity, not the independent truth of every claim.

## Related references

- [Catalog-wide audit and CI index](../AUDIT-AND-CI-INDEX.md)
- [Certificate test/evidence matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)
- [Spanish technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.md)
- [English technical report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.en.md)
