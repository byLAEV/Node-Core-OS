# Eight-Certificate Audit, Test Traceability, and GitHub Actions Index

**Audit date:** 2026-10-27  
**Baseline catalog integration:** `aa1b4bc43bb3f2a89dfb289119e033217bb77027`  
**Purpose:** trace each product profile to implementation, tests, GitHub Actions, recorded results, and evidence gaps.

## Executive finding

The implementation recognizes eight profile identifiers. Profile allowlisting is a certificate-format feature; it is **not** proof that each corresponding attack class has a dedicated passing effectiveness suite.

The repository has passing synthetic tests for identity binding, TLS, signed events, quorum decisions, certificate handling, and bounded API abuse. These results apply only to assertions actually executed. Product-specific effectiveness remains unproven for several profiles.

## Evidence categories

- **Envelope:** signature, issuer trust, claims, validity, revocation input, profile allowlist.
- **Related component:** nearby TLS, identity, quorum, API, or distributed-alert tests.
- **Product effectiveness:** dedicated scenarios for the attack class named by the product.
- **CI result:** completed run and conclusion tied to a specific tested commit.

## Source of truth

- [Certificate implementation](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/security/node_identity_certificate.py)
- [Certificate JSON Schema](https://github.com/byLAEV/Node-Core-OS/blob/main/schemas/node-core-node-identity-certificate.schema.json)
- [Certificate format specification](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/NODE-IDENTITY-CERTIFICATE-FORMAT.md)
- [Certificate envelope tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_node_identity_certificate.py)
- [Spanish technical security report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.md)
- [English technical security report](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.en.md)
- [Shield comparative campaign plan](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/shield/COMPARATIVE-GITHUB-ACTIONS-PLAN.md)

## GitHub Actions inventory

| Workflow | Actual scope | What it does not prove |
|---|---|---|
| [Certificate adversarial tests](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/certificate-adversarial-tests.yml) | Certificate/TLS/web-lab, Shield credentials and quorum, distributed alert acceptance, local distributed-defense primitives, bounded API abuse, compile checks | Dedicated effectiveness of all eight products |
| [Node Identity Certificate Conformance](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/node-identity-certificate.yml) | `pytest -q tests/test_node_identity_certificate.py` | That any profile's named attack is defeated |
| [Web2 Security Acceptance Report](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/web2-security-acceptance-report.yml) | Selected local Web2/identity/TLS/API tests and JSON/Markdown report artifact | Production WAF enforcement, volumetric DDoS, public PKI deployment, production IPFS convergence |
| [Shield Comparative Lab](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/shield-comparative-lab.yml) | Stage 0 regression suite and upload of the campaign plan | The full A/B campaign; the plan states NOT RUN / NOT COMPARABLE |

Relevant test sources:
- [Certificate security](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_certificate_security.py)
- [HTTPS certificate lab](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_certificate_web_lab.py)
- [Web TLS profile](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_web_tls_profile.py)
- [Standard HTTPS validation](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_standard_https_validation.py)
- [Distributed-defense primitives](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_distributed_defense.py)
- [Shield support credentials](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_shield_support.py)
- [Shield identity credentials](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_shield_identity_credential.py)
- [Shield web attack lab](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_shield_web_attack_lab.py)
- [Three-node alert acceptance](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_shield_distributed_alert_acceptance.py)
- [Bounded API abuse lab](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_api_abuse_lab.py)
- [P2P TLS transport](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_p2p_tls_transport.py)
- [Identity association tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_identity_associations.py)
- [Identity function tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_identity_function.py)

## Recorded CI results

| Run | Observed result | Scope / caveat |
|---|---|---|
| [#40450438209](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438209) | **SUCCESS**, completed job | Historical synthetic certificate/identity/TLS/Shield/API suite referenced by the security report. |
| [#40450434087](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450434087) | **SUCCESS**, completed job | Additional historical run; same bounded scope. |
| [#40500173588](https://github.com/byLAEV/Node-Core-OS/actions/runs/40500173588) | **SUCCESS**, completed job on PR head `a3ed04eb22deee5d4488d28dd7dd359d7bb77e0b` | The workflow sequence and compile step passed; not eight dedicated product suites. |
| [#40500173557](https://github.com/byLAEV/Node-Core-OS/actions/runs/40500173557) | **SUCCESS**; 36 tests in 8.417 seconds, `OK` | Synthetic Web2 acceptance. Artifact ZIP SHA-256: `d7340542470193e03494707d1318efbdbdbcf7f2f35b6e9c366c3c170e86615b`. Explicitly does not demonstrate volumetric DDoS, production Kubo/IPFS convergence, or all eight deployable web certificate profiles. |
| [#40450438106](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438106) | Linked in historical report | GNU/Linux CI; inspect this run's own result before assigning product coverage. |
| [#40450438099](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438099) | Linked in historical report | Kubo integration; not automatically proof of product 7's CID/content integrity claims. |
| [#40450438116](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438116) | Linked in historical report | Three-node P2P contracts; not automatically proof of eclipse resistance. |
| [#40450438162](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438162) | Linked in historical report | Three-node E2E; review exact assertions before mapping. |
| [#40450438183](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438183) | Linked in historical report | Installer E2E is not direct attack-resistance evidence. |
| [#40450438270](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438270) | Linked in historical report | Independent network domains; review exact assertions before mapping. |

The Web2 report artifact has a 30-day retention period from 2026-10-27 and may expire. Preserve a reviewed, non-sensitive summary with its commit and run URL for durable project records. Do not commit customer secrets or sensitive raw findings.

## Eight-product evidence status

| # | Profile | Evidence now established | Dedicated effectiveness suite |
|---:|---|---|---|
| 1 | `sybil-resistance` | Partial, indirect reporter/quorum tests | Not established |
| 2 | `p2p-partition-eclipse-resistance` | Partial, indirect TLS/three-node tests | Not established |
| 3 | `byzantine-collusion-resistance` | Partial, indirect signed-event/quorum tests | Not established |
| 4 | `identity-key-protection` | Direct certificate-envelope plus related identity/TLS tests | Partial; operational key lifecycle remains incomplete |
| 5 | `software-supply-chain-integrity` | Profile allowlisting only | Not established |
| 6 | `availability-ddos-resistance` | Bounded synthetic API abuse/rate-limit tests | No volumetric or production DDoS test |
| 7 | `ipfs-content-integrity` | Profile allowlisting; separate Kubo run needs assertion-level mapping | Not established |
| 8 | `privilege-and-pool-isolation` | Profile allowlisting only | Not established |

Each product folder must have its own `TEST-TRACEABILITY.md` identifying relevant tests, workflows, supported claims, and gaps.

## Critical audit findings

1. A profile ID is not an attack-prevention mechanism.
2. Historical green CI is tied to its tested SHA and must not be represented as a current-main result unless SHAs match.
3. Web2 acceptance is a bounded synthetic lab, not production proof.
4. Shield comparative stages 1–5 and its A/B verdict remain NOT RUN / NOT COMPARABLE.
5. Local revocation primitives do not prove distributed propagation, anti-rollback persistence, or disconnected-node recovery.
6. Distinct keys do not prove distinct people or independent operators; Sybil and collusion threats need dedicated tests.
7. Security testing must remain within loopback, private labs, or explicitly authorized scope.

## Audit acceptance criteria

- Every code profile maps to one product directory with README, service specification, evidence guide, and traceability file.
- Product pages state what tests actually establish and what they do not.
- Workflow names, test paths, run URLs, conclusions, and SHAs are not conflated.
- The catalog-integrity workflow passes.
- This audit does not define economic policy or implement payments.


## Latest evidence-based audit snapshot — 2026-10-28

See [Certificate Profiles — Evidence-Based Audit Snapshot](../../docs/CERTIFICATE-PROFILES-AUDIT-2026-10-28.md) for the current eight-profile status table, current-main CI runs, gaps, and prioritized next tests.

- Audited main commit: `98d53542cf89383fe237454485251a337978bee0`.
- [Catalog integrity run](https://github.com/byLAEV/Node-Core-OS/actions/runs/40623347474): SUCCESS on the audited commit.
- [Certificate adversarial tests](https://github.com/byLAEV/Node-Core-OS/actions/runs/40623347487): SUCCESS on the audited commit; synthetic bounded test scope only.
- [Three-node Kubo/P2P integration](https://github.com/byLAEV/Node-Core-OS/actions/runs/40622724911): SUCCESS on an earlier commit; cross-VM jobs were skipped and are not counted as passes.
