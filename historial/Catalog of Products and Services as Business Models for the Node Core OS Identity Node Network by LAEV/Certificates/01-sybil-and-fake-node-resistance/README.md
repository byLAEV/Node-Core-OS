# Sybil and Fake-Node Resistance Assessment

**Product ID:** `CERT-01`  
**Certificate profile:** `sybil-resistance`  
**Catalog status:** Proposed service definition  
**Economic policy:** `pending-consensus`

## What this product does

Assess whether a defined Node Core OS deployment has controls that make fabricated, duplicated, or misleading node participation harder to introduce or count as independent contribution.

This product is intended for authorized enterprise and institutional customers that need evidence-based security assessment of websites, Web2 applications, APIs, network infrastructure, or supporting services. Participating Node Core OS identities may execute approved work, submit evidence, and—where the service contract requires it—contribute to a jointly reviewed result.

## Business value

The service is designed to give a customer a documented view of a defined security question, including test scope, observations, evidence, limitations, and recommended corrective actions. It can support procurement, internal risk management, engineering decisions, or follow-up testing. It is not an automatic guarantee that a customer is secure.

## Threats and assessment objectives

- Multiple node identities controlled by one operator are mistaken for independent actors.
- Identity churn, fake enrollment, or fabricated activity distorts corroboration or service accounting.
- A provider's claimed organizational independence is accepted without evidence.

## Scope at a glance

- Review identity enrollment and admission rules within the authorized environment.
- Test whether the system distinguishes cryptographic keys from verified operator independence.
- Evaluate duplicate-task and repeated-evidence handling where implemented.

## Expected deliverables

- Threat model and test plan.
- Results for each synthetic identity/admission scenario.
- Evidence hashes, software version, configuration, limitations, and remediation recommendations.

## Acceptance principles

- Tests are authorized and reproducible.
- Each scenario has a stated expected outcome and observed result.
- The report distinguishes tested controls from unimplemented controls.
- No claim of universal Sybil resistance is made.

## Current implementation and testing status

The profile identifier is accepted by the certificate implementation. The current certificate unit tests check the envelope and unsupported-profile rejection; they do not constitute a complete Sybil-resistance benchmark. Related local corroboration tests are not proof of unique people or independent operators.

The `sybil-resistance` profile is defined in the project certificate implementation. A certificate profile identifier means the certificate format can name that assessment category; it does not by itself prove that all assessment methods described here are implemented or effective.

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
