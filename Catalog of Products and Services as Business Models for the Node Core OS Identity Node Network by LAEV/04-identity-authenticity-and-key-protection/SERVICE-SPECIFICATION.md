# Service Specification — Identity Authenticity and Key-Protection Assessment

## 1. Identification

- Product ID: `CERT-04`
- Profile: `identity-key-protection`
- Version: `0.1.0-draft`
- Status: `proposed`
- Economic policy: `pending-consensus`

## 2. Purpose

Assess whether node identity claims are cryptographically bound to keys and whether defined procedures protect signing authority, prevent impersonation, and handle key lifecycle events.

## 3. Preconditions

- The customer has documented authority over the assets and test environment.
- Scope, objectives, permitted methods, test window, contacts, and stop conditions are approved before execution.
- The provider identity and the key used to sign evidence are identified.
- Tool versions, target versions, configurations, and evidence retention requirements are recorded.
- Any production testing has explicit authorization and a risk-appropriate safety plan.

## 4. In-scope activities

- Verify certificate signatures, issuer trust configuration, time validity, and revocation behavior.
- Review key storage, permissions, rotation, recovery, and access controls within the agreed scope.
- Test rejection of malformed, altered, expired, or untrusted credentials.

## 5. Out of scope

- Unauthorized access, persistence, disruption, or testing of third-party assets.
- Claims about systems, versions, configurations, or periods not evaluated.
- Treating a cryptographic identity as proof of human uniqueness, honesty, or competence.
- Issuing a positive result solely because a certificate can be signed or verified.
- Publishing customer secrets, private keys, or sensitive vulnerability details without explicit approval.

## 6. Work unit and collaboration

The concrete technical work unit must be defined for each contract before execution. Examples may include one approved scenario, one verified artifact, one bounded measurement interval, or one independently reviewed report. A unit of work is a measurement definition, not a price or reward formula.

Where multiple nodes collaborate, the work order should identify each assigned subtask, its evidence, dependencies, and the combined acceptance condition. The future consensus policy will define how contributions are valued and paid; this specification does not allocate revenue.

## 7. Deliverables

- Certificate verification results.
- Key lifecycle and access-control findings.
- Issuer and revocation assumptions.
- Evidence and remediation report.

## 8. Acceptance criteria

- Negative cases are tested as well as valid cases.
- The trusted issuer source and revocation assumptions are documented.
- Private keys and secrets are not placed in public evidence.
- The report distinguishes key control from proof of human identity or honesty.

## 9. Evidence integrity

Evidence should identify the work order, target scope, relevant version, provider identity, tool version, timestamps, and hashes or signatures where appropriate. Evidence must be reviewable without exposing unnecessary personal data or secrets. A verifier should be able to distinguish raw observations, derived conclusions, and provider assertions.

## 10. Failure and dispute handling

The contract must define incomplete work, test interruption, ambiguous results, evidence gaps, retesting, rejection, appeal, and correction of records. Operational failure is not automatically fraud. Suspected manipulation should be handled under a documented incident process.

## 11. Economic policy

No price, fee, percentage, reward, or distribution formula is specified. All such values remain `pending-consensus` and must be approved separately before payment is enabled.

## 12. Required future approval

Before this service is marketed as operational, link a specific implementation, test evidence, review result, issuer policy, revocation method, and current limitation statement. Update the status only when supporting evidence exists.
