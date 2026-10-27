# Identity Authenticity and Key-Protection Assessment

**Product ID:** `CERT-04`  
**Certificate profile:** `identity-key-protection`  
**Catalog status:** Proposed service definition  
**Economic policy:** `pending-consensus`

## What this product does

Assess whether node identity claims are cryptographically bound to keys and whether defined procedures protect signing authority, prevent impersonation, and handle key lifecycle events.

This product is intended for authorized enterprise and institutional customers that need evidence-based security assessment of websites, Web2 applications, APIs, network infrastructure, or supporting services. Participating Node Core OS identities may execute approved work, submit evidence, and—where the service contract requires it—contribute to a jointly reviewed result.

## Business value

The service is designed to give a customer a documented view of a defined security question, including test scope, observations, evidence, limitations, and recommended corrective actions. It can support procurement, internal risk management, engineering decisions, or follow-up testing. It is not an automatic guarantee that a customer is secure.

## Threats and assessment objectives

- A forged or altered credential is accepted.
- A node identifier is confused with proof of civil identity or organizational authority.
- Compromised, leaked, expired, or replaced keys remain trusted.

## Scope at a glance

- Verify certificate signatures, issuer trust configuration, time validity, and revocation behavior.
- Review key storage, permissions, rotation, recovery, and access controls within the agreed scope.
- Test rejection of malformed, altered, expired, or untrusted credentials.

## Expected deliverables

- Certificate verification results.
- Key lifecycle and access-control findings.
- Issuer and revocation assumptions.
- Evidence and remediation report.

## Acceptance principles

- Negative cases are tested as well as valid cases.
- The trusted issuer source and revocation assumptions are documented.
- Private keys and secrets are not placed in public evidence.
- The report distinguishes key control from proof of human identity or honesty.

## Current implementation and testing status

The current certificate unit test suite includes a valid `identity-key-protection` certificate case and tests tampering, unknown issuers, revocation inputs, expiry, maximum lifetime, and unsupported profiles. These tests validate certificate-handling behavior, not a complete operational key-custody audit.

The `identity-key-protection` profile is defined in the project certificate implementation. A certificate profile identifier means the certificate format can name that assessment category; it does not by itself prove that all assessment methods described here are implemented or effective.

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
