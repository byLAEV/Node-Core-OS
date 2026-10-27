# Service Specification — Privilege Control and Enterprise-Pool Isolation

- **Product ID:** `CERT-08`
- **Certificate profile:** `privilege-and-pool-isolation`
- **Version:** `0.1.0-draft` | **Status:** `proposed`
- **Economic policy:** `pending-consensus`

## Purpose and method

Map roles, protected actions, organizational/service pools, data boundaries, and administrative paths. Execute authorized negative-access and cross-pool tests in a controlled environment to check whether permissions and isolation boundaries behave as specified.

## Deliverables

Permission and boundary matrix, actor/resource/action test cases, expected-versus-observed decisions, logs, affected versions, limitations, and remediation plan.

## Minimum acceptance criteria

- Each test identifies actor, resource, action, and expected authorization decision.
- Unauthorized actions and cross-pool access are rejected where policy requires.
- Test scope and software/configuration versions are recorded.
- Sensitive data and credentials are not copied into public reports.
- The report states which boundaries were tested and which remain unverified.

## Evidence record

Preserve the work-order reference, approved scope, role and pool identifiers, relevant configuration, exact test steps, expected and observed outcomes, timestamps, software version, and evidence hashes. Use synthetic or approved data wherever possible.

## Current testing boundary

The certificate profile is recognized, but certificate-envelope tests do not demonstrate application authorization, operating-system isolation, or enterprise-pool separation.

## Required next tests

Add least-privilege tests, unauthorized-action rejection, cross-tenant isolation, privilege-escalation attempts, and administrative/recovery boundary checks against the actual integrated controls.

## Failures, disputes, and economics

Record incomplete tests, ambiguous access decisions, and remediation/retest outcomes. Do not equate an operational mistake with intentional abuse without evidence. Prices, fees, provider/verifier shares, and distribution formulas remain `pending-consensus`; this specification does not authorize payment.
