# Identity Design Principles

**Status:** Normative design principles for implementation  
**Scope:** Node Core OS identity registration, node association, verification, and future security controls.

## 1. Design for legitimate use first

Node Core OS identity features must begin with a clear, accessible workflow for people acting in good faith. The initial experience must not treat every person as a suspect or make ordinary registration unnecessarily difficult.

The user should be able to enter the text fields from an identity document without uploading photographs, scans, or videos. Fields must adapt to the document type and issuing jurisdiction; the system must not require fields that do not apply.

This usability principle does not mean that declared information is automatically true or verified. The interface must clearly distinguish what a person entered from what a verification procedure has established.

## 2. Keep one persistent logical identity

A profile belongs to a persistent Node Core OS identity reference. Correcting a typographical error, renewing a document, changing an eligible attribute, recovering access, or rotating keys must not silently create a new logical identity.

Updates should preserve the identity reference and relevant history while allowing users to correct legitimate mistakes through an understandable process.

## 3. Distinguish declared data from verified evidence

At minimum, the system must distinguish:

- **Declared:** entered or confirmed by the user.
- **Verified:** checked by a named procedure with a recorded result and scope.
- **Pending / inconclusive / unavailable:** no positive or negative conclusion can yet be made.
- **Expired / revoked:** a previously valid piece of evidence is no longer current or accepted under its policy.
- **Discrepancy detected:** values do not match; this alone is not a finding of fraud.

Completing a form is not proof of civil identity, document authenticity, holder association, or uniqueness. A failed or unavailable external service must not be interpreted as evidence that the user is dishonest.

## 4. Make correct behavior easy and explainable

The interface should request only the information needed for the current purpose, explain why required fields are needed, validate formats, and allow review before saving. Errors should explain what needs attention and should not silently rewrite user data.

Differences may arise from spelling, formatting, legal name changes, document renewals, or data-source errors. The system should identify the discrepancy and support correction or review before assigning a meaning to it.

## 5. Keep personal data private by default

Identity profile data is private local data by default. It must not be automatically uploaded to Kubo/IPFS, published to a network, embedded in public logs, or committed to source control.

The initial terminal profile must:
- store its data under the user's local Node Core OS data directory;
- restrict local file permissions where the operating system supports them;
- avoid displaying the full identity-document number in the main menu;
- keep document numbers out of logs and diagnostics;
- avoid requiring photos, videos, or document uploads;
- require a separate, explicit design and authorization before any future external disclosure.

Local file permissions are a baseline, not a complete security solution. Encryption at rest, key management, backup, recovery, retention, and operating-system threat models require separate implementation and testing before the profile should be described as strongly protected.

## 6. Separate identity from node identity

A person's logical identity and a node's technical identifier are different concepts. A node identifier (for example, a Kubo Peer ID) identifies a network node, not a civil person.

Associating a profile with a node must be an explicit action. The association should be stored locally and displayed clearly. If the node has no available technical identifier, the profile may still be saved locally, but the interface must report that association is pending instead of inventing an identifier.

Node availability, control of a node key, civil identity, document authenticity, and personhood are separate claims and must not be collapsed into one status.

## 7. Design security controls after the legitimate workflow is clear

After the basic workflow is correct and usable, add proportionate security controls in independently testable layers:

1. Field and format validation.
2. Internal consistency checks.
3. Authorized issuer or provider corroboration.
4. Credential authenticity and revocation checks.
5. Evidence that the presenter is the legitimate holder, where required.
6. Duplicate-registration or Sybil-risk controls with an explicitly defined scope.
7. Auditable discrepancy handling, correction, appeal, and recovery.
8. Privacy-preserving selective disclosure where appropriate.

A mismatch is a signal to investigate, not automatic proof of a lie. No single score or boolean should imply that every identity property has been verified. Any verification result must name the procedure, source, time, scope, status, and known limitations.

## 8. Do not overclaim verification or security

A completed local form means only that required fields were entered. It does not prove the identity data is authentic. A valid signature proves a cryptographic relationship under a key and trust policy; it does not, by itself, prove that a real-world person is the key holder.

Any future assurance level must be based on explicit policies, independent tests, documented limitations, and review of failure modes. Features must be labelled planned until implemented and tested.

## 9. Implementation acceptance criteria

The first identity-profile implementation is acceptable only if tests demonstrate that:

- a user can enter identity-document data as text without attachments;
- the profile persists across menu sessions;
- a stable logical identity reference is retained when the profile is edited;
- node association is explicit and uses a real, available node identifier;
- the main menu reflects the saved name, alias, nationality, and node-association status;
- the full document number is not displayed in the main menu;
- identity data is stored locally and is not sent to IPFS or another network service;
- missing node identifiers and incomplete verification are explained without treating them as fraud;
- tests use synthetic data and do not embed real identity numbers or personal records in the repository.

These principles guide the implementation of Node Core OS. They do not claim that all future security controls or identity-verification mechanisms already exist.
