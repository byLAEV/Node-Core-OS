# Certificate Test and Evidence Matrix

This matrix separates **profile registration**, **certificate-envelope tests**, and **security-effectiveness evidence**. They are different claims and must not be reported as interchangeable.

## Existing certificate-envelope tests

Source: [`tests/test_node_identity_certificate.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_node_identity_certificate.py)

The current unit tests cover:
- valid certificate issuance and verification;
- payload tampering rejection;
- unknown issuer rejection;
- revocation rejection when a revoked-ID set is supplied;
- expiry rejection;
- rejection of an issuance lifetime exceeding 90 days;
- rejection of an unsupported profile.

The profile allowlist is defined in [`node_core/security/node_identity_certificate.py`](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/security/node_identity_certificate.py). The dedicated workflow is [`node-identity-certificate.yml`](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/node-identity-certificate.yml).

These tests demonstrate behavior of the certificate implementation for the tested cases. They do **not** prove that all eight types of attacks are prevented in a live or production network.

## Per-product evidence matrix

| # | Profile | Existing relevant evidence | Dedicated effectiveness tests required |
|---:|---|---|---|
| 1 | `sybil-resistance` | Profile is recognized; distributed-defense code has local corroboration primitives and related tests | Sybil identities controlled by one operator, fake enrollment, identity churn, collusion, false independence claims |
| 2 | `p2p-partition-eclipse-resistance` | Profile is recognized; existing P2P/TLS tests cover only their named transport cases | Peer-table poisoning, eclipse simulation, partitions, recovery, peer diversity, stale peer data |
| 3 | `byzantine-collusion-resistance` | Profile is recognized; local corroboration primitives have related tests | Byzantine behavior, coordinated conflicting reports, quorum safety/liveness, collusion and recovery |
| 4 | `identity-key-protection` | Used by the certificate unit test; identity, TLS, and certificate-related tests exist | Key compromise, rotation/recovery, unauthorized signing, storage permissions, revocation distribution, operational key custody |
| 5 | `software-supply-chain-integrity` | Profile is recognized by certificate implementation | Dependency tampering, artifact provenance, signature validation, reproducible build and update rollback |
| 6 | `availability-ddos-resistance` | Profile is recognized; limited API-abuse laboratory tests are documented elsewhere | Authorized rate/load tests, resource exhaustion controls, service degradation/recovery, distributed load limits; no uncontrolled public DDoS |
| 7 | `ipfs-content-integrity` | Profile is recognized; repository has Kubo/IPFS integration areas | CID/content mismatch, retrieval integrity, unavailable blocks, malicious content handling, pin/retention claims |
| 8 | `privilege-and-pool-isolation` | Profile is recognized by certificate implementation | Cross-pool access attempts, least privilege, authorization boundaries, tenant data separation, privilege escalation |

## CI references

- [Node Identity Certificate Conformance workflow](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/node-identity-certificate.yml)
- [Certificate adversarial test workflow](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/certificate-adversarial-tests.yml)
- [Existing certificate and identity security report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.md)

For historic run details and scope, consult the report and the linked GitHub Actions run pages. A workflow file proves that a test job is defined; only a completed run tied to the relevant commit proves that the job ran successfully for that revision.

## Rules for publishing results

For each new test suite, record the commit SHA, workflow run URL, test command, environment, outcome, test count where available, known limitations, and whether the run applies to the exact code being advertised. Never turn a profile allowlist test into a claim that the related attack is defeated. Never claim production readiness from a synthetic loopback test alone.
