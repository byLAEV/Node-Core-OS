# Service Specification — Software Supply-Chain and Update Integrity Assessment

## 1. Identification

- Product ID: `CERT-05`
- Profile: `software-supply-chain-integrity`
- Version: `0.1.0-draft`
- Status: `proposed`
- Economic policy: `pending-consensus`

## 2. Purpose

Assess provenance and integrity controls for software artifacts, dependencies, builds, and updates used by an authorized organization or node deployment.

## 3. Preconditions

- The customer has documented authority over the assets and test environment.
- Scope, objectives, permitted methods, test window, contacts, and stop conditions are approved before execution.
- The provider identity and the key used to sign evidence are identified.
- Tool versions, target versions, configurations, and evidence retention requirements are recorded.
- Any production testing has explicit authorization and a risk-appropriate safety plan.

## 4. In-scope activities

- Inspect artifact hashes, signature verification, dependency pinning, and provenance records where available.
- Test tampering and invalid-signature scenarios against the defined verification process.
- Review update authorization and rollback controls.

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

- Artifact inventory and version identifiers.
- Verification outcomes and provenance gaps.
- Reproducible test evidence and remediation guidance.

## 8. Acceptance criteria

- The tested artifact and exact version are identified.
- Valid and invalid artifact cases are covered.
- The process records provenance and explains unverified dependencies.
- No claim of supply-chain security is made solely from a valid certificate signature.

## 9. Evidence integrity

Evidence should identify the work order, target scope, relevant version, provider identity, tool version, timestamps, and hashes or signatures where appropriate. Evidence must be reviewable without exposing unnecessary personal data or secrets. A verifier should be able to distinguish raw observations, derived conclusions, and provider assertions.

## 10. Failure and dispute handling

The contract must define incomplete work, test interruption, ambiguous results, evidence gaps, retesting, rejection, appeal, and correction of records. Operational failure is not automatically fraud. Suspected manipulation should be handled under a documented incident process.

## 11. Economic policy

No price, fee, percentage, reward, or distribution formula is specified. All such values remain `pending-consensus` and must be approved separately before payment is enabled.

## 12. Required future approval

Before this service is marketed as operational, link a specific implementation, test evidence, review result, issuer policy, revocation method, and current limitation statement. Update the status only when supporting evidence exists.
