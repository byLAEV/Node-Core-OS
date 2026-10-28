# Byzantine Fault and Node-Collusion Resistance Assessment

**Product ID:** `CERT-03`  
**Certificate profile:** `byzantine-collusion-resistance`  
**Catalog status:** Proposed service definition  
**Economic policy:** `pending-consensus`

## What this product does

Evaluate a defined protocol's response to faulty, inconsistent, delayed, or coordinated participants, including the safety and liveness assumptions of its decision rules.

This product is intended for authorized enterprise and institutional customers that need evidence-based security assessment of websites, Web2 applications, APIs, network infrastructure, or supporting services. Participating Node Core OS identities may execute approved work, submit evidence, and—where the service contract requires it—contribute to a jointly reviewed result.

## Business value

The service is designed to give a customer a documented view of a defined security question, including test scope, observations, evidence, limitations, and recommended corrective actions. It can support procurement, internal risk management, engineering decisions, or follow-up testing. It is not an automatic guarantee that a customer is secure.

## Threats and assessment objectives

- Conflicting reports or state transitions are accepted.
- A colluding group manipulates corroboration or quorum assumptions.
- Fault handling prevents progress or accepts unsafe state.

## Scope at a glance

- Document the protocol, fault assumptions, quorum, and trust boundaries.
- Run deterministic synthetic scenarios for conflicting, missing, delayed, and repeated messages.
- Evaluate whether the result follows the documented protocol under tested conditions.

## Expected deliverables

- Threat model and assumed maximum fault/collusion scope.
- Scenario definitions, logs, and reproducible test outputs.
- Safety/liveness observations and remediation items.

## Acceptance principles

- The assumptions and quorum rules are explicit.
- Each test has reproducible inputs and expected outcomes.
- Findings separate local corroboration logic from end-to-end distributed consensus.
- No universal Byzantine fault tolerance claim is made without a protocol-specific proof and tests.

## Current implementation and testing status

The profile identifier is accepted by the certificate implementation. Existing local corroboration primitives may be relevant but do not prove Byzantine fault tolerance or independence of identities. Dedicated protocol-level fault-injection tests remain necessary.

The `byzantine-collusion-resistance` profile is defined in the project certificate implementation. A certificate profile identifier means the certificate format can name that assessment category; it does not by itself prove that all assessment methods described here are implemented or effective.

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
