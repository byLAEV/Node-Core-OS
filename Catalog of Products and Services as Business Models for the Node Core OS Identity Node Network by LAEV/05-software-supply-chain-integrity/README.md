# Software Supply-Chain and Update Integrity Assessment

**Product ID:** `CERT-05`  
**Certificate profile:** `software-supply-chain-integrity`  
**Catalog status:** Proposed service definition  
**Economic policy:** `pending-consensus`

## What this product does

Assess provenance and integrity controls for software artifacts, dependencies, builds, and updates used by an authorized organization or node deployment.

This product is intended for authorized enterprise and institutional customers that need evidence-based security assessment of websites, Web2 applications, APIs, network infrastructure, or supporting services. Participating Node Core OS identities may execute approved work, submit evidence, and—where the service contract requires it—contribute to a jointly reviewed result.

## Business value

The service is designed to give a customer a documented view of a defined security question, including test scope, observations, evidence, limitations, and recommended corrective actions. It can support procurement, internal risk management, engineering decisions, or follow-up testing. It is not an automatic guarantee that a customer is secure.

## Threats and assessment objectives

- An artifact or dependency is substituted without detection.
- An update is unsigned, incorrectly signed, or delivered from an untrusted source.
- Rollback or build provenance gaps allow vulnerable or unreviewed code to be deployed.

## Scope at a glance

- Inspect artifact hashes, signature verification, dependency pinning, and provenance records where available.
- Test tampering and invalid-signature scenarios against the defined verification process.
- Review update authorization and rollback controls.

## Expected deliverables

- Artifact inventory and version identifiers.
- Verification outcomes and provenance gaps.
- Reproducible test evidence and remediation guidance.

## Acceptance principles

- The tested artifact and exact version are identified.
- Valid and invalid artifact cases are covered.
- The process records provenance and explains unverified dependencies.
- No claim of supply-chain security is made solely from a valid certificate signature.

## Current implementation and testing status

The profile identifier is accepted by the certificate implementation. The certificate-envelope tests do not test dependency integrity, reproducible builds, artifact signing, or update rollback. Dedicated supply-chain tests must be added.

The `software-supply-chain-integrity` profile is defined in the project certificate implementation. A certificate profile identifier means the certificate format can name that assessment category; it does not by itself prove that all assessment methods described here are implemented or effective.

See:
- [Service specification](./SERVICE-SPECIFICATION.md)
- [Evidence and testing guide](./EVIDENCE-AND-TESTING.md)
- [Catalog-wide test matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)
- [Certificate implementation](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/security/node_identity_certificate.py)

## Commercial status

This is a proposed service definition. Price, provider remuneration, verifier remuneration, fees, and allocation of revenue are **not defined**. They must be decided by the business-model consensus process. No revenue or customer demand is guaranteed.

## Important limitation

A certificate records defined claims made under an issuer and verification policy. A valid signature establishes integrity and key-based origin of the signed claims; it does not prove every claim is true. The final report must state the exact system, version, period, methods, results, exclusions, and known limitations.


## Audit and evidence traceability

- [Test traceability and GitHub Actions mapping](./TEST-TRACEABILITY.md)
- [Service specification](./SERVICE-SPECIFICATION.md)
- [Evidence and testing guide](./EVIDENCE-AND-TESTING.md)
- [Catalog-wide audit and CI index](../AUDIT-AND-CI-INDEX.md)
