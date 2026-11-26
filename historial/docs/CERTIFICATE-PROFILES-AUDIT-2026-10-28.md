# Certificate Profiles — Evidence-Based Audit Snapshot

**Audit date:** 2026-10-28  
**Audited revision:** `98d53542cf89383fe237454485251a337978bee0`  
**Scope:** Eight certificate profile identifiers, their shared implementation, documented test mapping, and latest checked CI results.  
**Audit type:** Repository/documentation review plus inspection of linked test and workflow definitions. This is not an independent security audit.

## Executive finding

The implementation at `node_core/security/node_identity_certificate.py` recognizes all eight profile identifiers in a single allowlist. It implements a common signed JWS/Ed25519 certificate envelope, issuer-key trust lookup, validity checks, a maximum 90-day lifetime, local revocation-ID rejection, and bounded metadata.

**This shared envelope does not implement the eight security products themselves.** The catalog entries remain proposed service definitions. Only profile 4 has direct certificate-envelope evidence for its named identifier; profiles 1–3 and 6 have partial, indirect evidence from related components; profiles 5, 7, and 8 currently have only profile-allowlist evidence in the product traceability records.

## Revision and current CI evidence

Audited `main` commit: [`98d53542`](https://github.com/byLAEV/Node-Core-OS/commit/98d53542cf89383fe237454485251a337978bee0), which includes PR #179.

- [Certificate catalog integrity — SUCCESS](https://github.com/byLAEV/Node-Core-OS/actions/runs/40623347474), same audited commit. The job validates catalog structure and traceability files; it is not a security-effectiveness benchmark.
- [Certificate adversarial tests — SUCCESS](https://github.com/byLAEV/Node-Core-OS/actions/runs/40623347487), same audited commit. The workflow runs synthetic certificate, identity, TLS, Shield/quorum, distributed-alert, bounded API-abuse and compile checks as defined in `.github/workflows/certificate-adversarial-tests.yml`. The passing run establishes only the assertions in that workflow.
- [Three-node Kubo/P2P integration — SUCCESS](https://github.com/byLAEV/Node-Core-OS/actions/runs/40622724911), commit `91f6158e99e0535a3db42c33ebe61b5c131c1f5b`, **not** the audited `main` SHA. The GNU/Linux terminal and three-node P2P jobs passed. The separate-VM manifest-convergence and cross-VM matrix jobs were skipped. Therefore this run is related evidence, not current-commit proof of cross-VM convergence.

## Eight-profile status table

| # | Profile | Code present | Existing evidence | Current classification | Main missing acceptance evidence |
|---:|---|---|---|---|---|
| 1 | `sybil-resistance` | Shared allowlist entry only for this profile; related corroboration/identity components exist elsewhere | Signed reporter identity, receiver-owned quorum policy, repeated-report rejection and selected three-node loopback tests | **PARTIAL / INDIRECT**; proposed service | Single-operator/multi-key, fake enrollment, identity churn, duplicate work, collusion and false-independence scenarios |
| 2 | `p2p-partition-eclipse-resistance` | Shared allowlist entry; separate P2P/TLS code exists | Peer identity/pinning and selected three-node loopback partition/recovery behavior | **PARTIAL / INDIRECT**; proposed service | Peer-table poisoning, eclipse simulation, peer diversity, stale peers, bounded partition duration and recovery invariants |
| 3 | `byzantine-collusion-resistance` | Shared allowlist entry; related local corroboration primitives exist | Signed-event validity, trust, expiry, tamper/replay rejection, quorum thresholds and selected three-node scenarios | **PARTIAL / INDIRECT**; proposed service | Explicit Byzantine fault model, conflicting proposals, quorum safety/liveness boundaries, coordinated collusion and recovery |
| 4 | `identity-key-protection` | Shared certificate envelope plus node identity and TLS components | Certificate issue/verify, tampering, unknown issuer, supplied revocation set, expiry/lifetime and unsupported-profile rejection; related identity/TLS tests | **DIRECT FOR ENVELOPE; PARTIAL FOR OPERATIONAL SECURITY**; proposed service | Issuer-ID/key binding, key rotation/recovery, unauthorized signing, custody/permissions, revocation propagation and anti-rollback |
| 5 | `software-supply-chain-integrity` | Shared allowlist entry | Generic envelope tests only | **PROFILE ONLY; NO DEDICATED EFFECTIVENESS TEST**; proposed service | Artifact provenance, dependency-tampering fixtures, reproducible-build comparison, signed-update verification and rollback rejection |
| 6 | `availability-ddos-resistance` | Shared allowlist entry; bounded API-abuse lab exists | Synthetic malformed/oversized request and bounded rate-limit scenarios | **PARTIAL / BOUNDED API LAB ONLY**; proposed service | Isolated resource-exhaustion/recovery tests, resource and latency metrics, error thresholds and documented abort criteria. No public volumetric DDoS testing |
| 7 | `ipfs-content-integrity` | Shared allowlist entry; Kubo/IPFS integration exists separately | Kubo workflows exist, but not every passing Kubo job proves the product-specific CID/content claims | **PROFILE ONLY / NEEDS ASSERTION-LEVEL MAPPING**; proposed service | Correct/mismatched CID fixtures, missing-block/retrieval failures, pin/retention behavior and safe untrusted-content handling |
| 8 | `privilege-and-pool-isolation` | Shared allowlist entry | Generic profile-allowlist/envelope tests only | **PROFILE ONLY; NO DEDICATED EFFECTIVENESS TEST**; proposed service | Actor/resource/action authorization matrix, cross-pool negative access, least privilege, privilege escalation and administrative/recovery boundaries |

Each profile's detailed traceability document remains the source for its test paths and per-product gaps:
- [CERT-01 — Sybil](../Catalog%20of%20Products%20and%20Services%20as%20Business%20Models%20for%20the%20Node%20Core%20OS%20Identity%20Node%20Network%20by%20LAEV/Certificates/01-sybil-and-fake-node-resistance/TEST-TRACEABILITY.md)
- [CERT-02 — P2P partition/eclipsing](../Catalog%20of%20Products%20and%20Services%20as%20Business%20Models%20for%20the%20Node%20Core%20OS%20Identity%20Node%20Network%20by%20LAEV/Certificates/02-p2p-partition-and-eclipse-resistance/TEST-TRACEABILITY.md)
- [CERT-03 — Byzantine/collusion](../Catalog%20of%20Products%20and%20Services%20as%20Business%20Models%20for%20the%20Node%20Core%20OS%20Identity%20Node%20Network%20by%20LAEV/Certificates/03-byzantine-fault-and-collusion-resistance/TEST-TRACEABILITY.md)
- [CERT-04 — Identity/key protection](../Catalog%20of%20Products%20and%20Services%20as%20Business%20Models%20for%20the%20Node%20Core%20OS%20Identity%20Node%20Network%20by%20LAEV/Certificates/04-identity-authenticity-and-key-protection/TEST-TRACEABILITY.md)
- [CERT-05 — Supply chain](../Catalog%20of%20Products%20and%20Services%20as%20Business%20Models%20for%20the%20Node%20Core%20OS%20Identity%20Node%20Network%20by%20LAEV/Certificates/05-software-supply-chain-integrity/TEST-TRACEABILITY.md)
- [CERT-06 — Availability/DDoS](../Catalog%20of%20Products%20and%20Services%20as%20Business%20Models%20for%20the%20Node%20Core%20OS%20Identity%20Node%20Network%20by%20LAEV/Certificates/06-availability-and-ddos-resilience/TEST-TRACEABILITY.md)
- [CERT-07 — IPFS content integrity](../Catalog%20of%20Products%20and%20Services%20as%20Business%20Models%20for%20the%20Node%20Core%20OS%20Identity%20Node%20Network%20by%20LAEV/Certificates/07-ipfs-content-integrity/TEST-TRACEABILITY.md)
- [CERT-08 — Privilege/pool isolation](../Catalog%20of%20Products%20and%20Services%20as%20Business%20Models%20for%20the%20Node%20Core%20OS%20Identity%20Node%20Network%20by%20LAEV/Certificates/08-privilege-control-and-pool-isolation/TEST-TRACEABILITY.md)

## Next test order

1. **CERT-04 — Identity/key protection:** strongest direct code/test foundation; add issuer binding, rotation/recovery, unauthorized signing and revocation-propagation tests.
2. **CERT-07 — IPFS content integrity:** map existing Kubo tests to exact content-integrity assertions before claiming coverage; add mismatched-CID and missing-block cases.
3. **CERT-02 — P2P partition/eclipsing:** use the existing three-node lab to add bounded peer-poisoning, peer-diversity and partition/recovery invariants.
4. **CERT-01 and CERT-03 — Sybil/Byzantine:** define explicit attacker assumptions and independent-operator limitations before implementing synthetic attack cases.
5. **CERT-05 and CERT-08 — Supply chain and isolation:** currently profile-only; define interfaces and acceptance criteria before coding product-specific tests.
6. **CERT-06 — Availability:** expand bounded, isolated resource and recovery tests only; do not perform uncontrolled public DDoS.

## Audit limitations

- This was a repository and test-definition review, not an independent cryptographic review or live production penetration test.
- Test definitions and green workflow runs are evidence only for their exact revision and assertions.
- The P2P run above belongs to an earlier commit, and its cross-VM jobs were skipped.
- No product is approved for commercial delivery by this audit.
- Do not infer human identity, independent ownership, production availability, or universal attack resistance from a key, profile identifier, or passing synthetic test.
