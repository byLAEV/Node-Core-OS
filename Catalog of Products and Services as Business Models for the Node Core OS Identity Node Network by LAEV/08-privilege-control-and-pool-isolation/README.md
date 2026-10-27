# 8. Privilege Control and Enterprise-Pool Isolation

**Profile:** `privilege-and-pool-isolation` | **Catalog status:** Proposed | **Economic policy:** Pending consensus

## Product purpose

Assess whether roles, permissions, tenant boundaries, and service pools prevent unauthorized access or unintended cross-organization data and control flow.

## Assessment objectives

- Map roles, protected actions, pools, and data boundaries.
- Run authorized negative-access and cross-pool isolation tests in a controlled environment.
- Review least privilege, secret handling, logging, and administrative recovery.
- Document which boundaries were tested and which remain unverified.

## Deliverables

Permission and boundary matrix, expected-versus-observed access decisions, test logs, affected versions, limitations, and remediation plan.

## Acceptance principles

Each test identifies actor, resource, action, and expected decision; unauthorized access must be rejected; reports must not expose sensitive data. Do not claim all tenants or pools are isolated unless they were actually tested.

## Current testing boundary

The profile identifier exists. Certificate-envelope tests do not demonstrate application authorization, operating-system isolation, or enterprise-pool separation. Dedicated tests against integrated controls are required.

See [service specification](./SERVICE-SPECIFICATION.md) and the [catalog test matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md).


## Audit and evidence traceability

- [Test traceability and GitHub Actions mapping](./TEST-TRACEABILITY.md)
- [Service specification](./SERVICE-SPECIFICATION.md)
- [Evidence and testing guide](./EVIDENCE-AND-TESTING.md)
- [Catalog-wide audit and CI index](../AUDIT-AND-CI-INDEX.md)
