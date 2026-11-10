# Service Specification — BICDN Bitcoin Conflict Declaration and Resolution Certificate

## 1. Identification

- Product ID: `BICDN-01`
- Profile: `bitcoin-conflict-declaration`
- Version: `0.1.0-draft`
- Status: `proposed`
- Target adopters: exchanges, custodians, Bitcoin service providers, law firms, media organizations, investigative organizations, and competent institutions.
- Product role: independent documentation and interoperability infrastructure; not a competing complaint desk.

## 2. Actors and responsibilities

- **Declarant:** completes and submits the initial form; chooses identity and disclosure mode.
- **Certificate issuer:** validates the form's structural requirements, records the issuer identity/key, signs the issued declaration, and states exactly what was checked.
- **Identity node:** stores or replicates authorized public metadata and encrypted objects according to retention and access policy.
- **Contributor:** submits additional information; may be anonymous, pseudonymous, or identified.
- **Institution:** integrates BICDN into its existing intake procedure and may append a signed receipt, case reference, response, or decision.
- **Lawyer:** may accept a confidential contact request and communicate through a restricted channel, subject to professional duties and applicable identity checks.
- **Expert/reviewer/mediator:** contributes an attributed report or process event; must disclose conflicts of interest.
- **External resolution provider:** operates its own rules and process. BICDN records references and signed outcomes; it does not control the provider.
- **Verifier:** checks signatures, hashes, issuer trust, event links, and status without being required to agree with the claims.

A key or node identity proves control of a key under a trust policy, not civil identity, one-person-one-account, competence, independence, or honesty. Any stronger identity claim requires a separate assurance process.

## 3. Declaration form

The form should capture, where applicable:

- Case title and conflict category.
- Declarant identity mode: `identified`, `pseudonymous`, or `anonymous`.
- Declarant identity reference, only if voluntarily or lawfully provided.
- Statement of events and requested assistance.
- Relevant Bitcoin network, transaction IDs, addresses, block references, wallet/service/exchange names, and approximate event times.
- Parties and organizations involved, clearly marked as declarant assertions unless independently established.
- Jurisdiction relationships and their status.
- Evidence manifest: description, media type, digest, encrypted storage reference, provenance and disclosure policy.
- Requested institutional recipients and permitted disclosure scope.
- Consent, retention, and contact preferences.
- External resolution access preferences.

A form can be submitted without evidence. Empty optional evidence arrays are valid. The system must not fabricate case IDs, legal references, transaction identifiers, or jurisdiction determinations.

## 4. Certificate and event model

The issued certificate contains the canonical initial declaration and an immutable reference to it. Later contributions are separate case events, each with its own event ID, timestamp, author/identity mode, signature or anonymous-ingress attestation, content digest, visibility policy, and previous-event/reference links.

Recommended event types include:

- `DECLARATION_SUBMITTED`
- `CERTIFICATE_ISSUED`
- `EVIDENCE_ADDED`
- `ANONYMOUS_CONTRIBUTION_RECEIVED`
- `INSTITUTIONAL_RECEIPT_RECORDED`
- `INSTITUTIONAL_RESPONSE_ADDED`
- `JURISDICTION_RELATION_ADDED`
- `LEGAL_CONTACT_REQUESTED`
- `LEGAL_REPRESENTATIVE_ACCEPTED`
- `SECURE_CHANNEL_OPENED`
- `EXPERT_REPORT_ADDED`
- `MEDIATION_STARTED`
- `CONSENSUS_REPORT_ADDED`
- `RESOLUTION_OUTCOME_RECORDED`
- `CORRECTION_OR_SUPERSEDING_EVENT_ADDED`
- `ACCESS_REVOKED` (does not erase prior public metadata or copies)

No participant may silently edit or erase another participant's signed event. Corrections are new events referencing the item corrected. The case ledger should distinguish event ordering from wall-clock claims; timestamps require a declared source and assurance level.

## 5. Jurisdiction registry

Each jurisdiction relationship must include a country/territory code where known, relationship type, status, source/evidence reference, submitter, and timestamp. Suggested relationship types: claimant residence, respondent incorporation, place of event, contractual governing law, asset/service location, authority receiving a complaint, or proceeding venue.

Allowed status values:

- `declared`: asserted by a participant, not legally determined.
- `documented`: supported by a referenced document or reliable record, not necessarily a determination of competence.
- `recognized`: backed by an explicit determination or official record from a competent authority, with a reference.

The certificate must not infer that a court or authority has jurisdiction merely because a country is listed. Applicable law, venue, jurisdiction, admissibility, and enforceability remain matters for competent legal analysis and decision.

## 6. Anonymous and confidential contributions

Anonymous contributions may omit a public identity reference. The system should distinguish anonymous, pseudonymous, and identified modes. An anonymous ingress service may use rate limits, abuse prevention, proof-of-work or privacy-preserving anti-spam measures where appropriate, but must not describe these controls as identity verification.

- Public case views should expose only fields authorized for public disclosure.
- Sensitive messages and evidence should be encrypted before distributed storage.
- Public IPFS CIDs are not access control; encrypt content before publication and manage keys separately.
- Avoid placing personal data, private keys, seed phrases, unredacted identity documents, or confidential legal communications in public metadata.
- Do not promise absolute anonymity: network metadata, uploaded-file metadata, timing, and recipient handling can reveal information.
- Do not promise permanent availability from IPFS alone; replication, pinning, retrieval monitoring, and retention policy are separate operational requirements.
- Anonymous submissions are allegations/information received, not automatically verified evidence.

## 7. Legal Contact Protocol

A contribution may request communication through a lawyer. The request is a case event, not proof that a lawyer-client relationship exists.

Suggested flow:

1. Contributor submits `LEGAL_CONFIDENTIAL_CONTACT_REQUEST` with anonymous/pseudonymous/identified mode.
2. BICDN records only the public event metadata and a digest/reference for the encrypted message.
3. A participating lawyer or legal organization receives the request through an authorized private gateway.
4. The lawyer may accept, decline, or request additional information through the gateway.
5. If accepted, the parties establish a secure channel and define what, if anything, may be appended to the public case ledger.
6. Identity verification, conflicts checks, client intake, privilege, confidentiality, and anti-money-laundering duties are handled by the lawyer under applicable law.

Do not claim that a message is legally privileged merely because it is encrypted or labelled confidential. Do not expose a lawyer's or contributor's contact details in public case metadata.

## 8. External Conflict Resolution Access

The certificate may provide a resolution-access reference or service discovery entry. It can connect the holder to independent technical experts, reviewers, consensus panels, mediators, and arbitration providers.

- Technical consensus means a documented convergence/divergence of expert opinions, not a court judgment.
- Mediation is voluntary and does not impose a result unless the parties enter a valid agreement.
- Arbitration requires consent, applicable rules, a defined seat/law where appropriate, and enforceability analysis.
- Institutions retain their own complaint procedures and legal authority.
- BICDN records participation, methods, declarations of interest, dissent, reports, and outcomes; it does not guarantee a favorable resolution.

## 9. Institutional integration

Provide a documented API/SDK contract in a future implementation for:
- verify certificate and event signatures;
- retrieve authorized case metadata;
- submit an institutional receipt and internal case reference;
- append a signed response or status update;
- request permission to access restricted evidence;
- link a provider's own case ID to the BICDN case ID;
- publish a signed outcome or referral.

An institution can use BICDN to support its own procedure. It does not delegate its legal decision-making to Node Core OS, and BICDN does not certify the institution's fairness merely because it integrates the protocol.

## 10. Storage, propagation, and synchronization

Use a local durable store plus distributed content-addressed storage where suitable. Replicate event envelopes and encrypted evidence according to explicit policy. Each event should have a canonical digest and signature/attestation, and reference its case and relevant predecessor(s). Synchronization must be idempotent, detect conflicting event IDs, retain provenance, and reconcile concurrent events without overwriting them.

IPFS content addressing can help detect content changes; it does not itself provide confidentiality, legal retention, guaranteed pinning, or censorship-proof universal availability. Define replication targets, pinning responsibility, deletion/legal-hold policy, key recovery, and unavailable-node behavior before production.

## 11. Security and privacy requirements

- Canonical serialization before signing; reject ambiguous or duplicate JSON keys.
- Use established cryptographic libraries and versioned algorithms; do not invent cryptography.
- Separate issuer keys, contributor keys, encryption keys, and institutional keys.
- Support key rotation, revocation status, recovery policy, and audit logs.
- Validate schemas and bound all text, arrays, file sizes, and references.
- Sanitize uploaded content and never execute submitted files.
- Use access control for restricted data and minimize metadata leakage.
- Publish threat models for Sybil submissions, spam, coercion, malicious allegations, deanonymization, collusion, and storage-provider failure.
- Provide dispute/appeal and correction processes without rewriting history.

## 12. Acceptance criteria for a future implementation

A production claim requires, at minimum:

1. Valid and invalid form fixtures pass strict JSON Schema validation.
2. Certificate issuance signs canonical claims and rejects tampering/unknown issuers.
3. Event ledger detects duplicate IDs, broken references, altered payloads, and replay.
4. Two or more test nodes synchronize events idempotently and reconcile concurrent additions.
5. Anonymous contribution flow does not require a public identity and has documented metadata/privacy limits.
6. Restricted evidence is encrypted before storage; unauthorized access tests fail safely.
7. Jurisdiction statuses remain distinct and no automatic competence inference occurs.
8. Institutional receipt/response signatures are independently verifiable.
9. Legal-contact workflow keeps messages and contact details restricted.
10. Resolution reports preserve method, participants, conflicts, dissent, and limitations.
11. Retention, revocation, recovery, and node outage behavior are tested.
12. Independent security and privacy review is completed before production marketing.

## 13. Current status and non-claims

This specification and accompanying schemas are a draft. No operational BICDN issuance, anonymous ingress, IPFS replication guarantee, lawyer network, institutional gateway, consensus engine, arbitration, or production security validation is implemented by this documentation change. Do not add the BICDN profile to the existing node identity certificate allowlist until the separate application-level credential envelope, trust policy, and tests are implemented and reviewed.
