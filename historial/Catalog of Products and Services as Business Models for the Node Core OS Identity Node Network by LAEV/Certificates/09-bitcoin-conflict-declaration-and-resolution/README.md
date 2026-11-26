# BICDN — Bitcoin Conflict Declaration and Resolution Certificate

**Product ID:** `BICDN-01`  
**Certificate profile:** `bitcoin-conflict-declaration`  
**Version:** `0.1.0-draft`  
**Status:** `proposed` — documentation and schema proposal only  
**Economic policy:** `pending-consensus`

## Purpose

BICDN is a portable, cryptographically verifiable conflict-declaration record for people and organizations dealing with disputes, incidents, claims, or other problems related to Bitcoin. It is designed primarily as infrastructure that exchanges, custodians, service providers, law firms, media organizations, and competent institutions can integrate into their existing intake and case-management procedures. It is not intended to replace those organizations or compete with their complaint services.

The certificate is a structured form that becomes a versioned case record after issuance. It can be referenced by multiple institutions and jurisdictions, receive separately attributed additions (including anonymous contributions), preserve a verifiable event history, and provide an access path to independent external analysis, consensus, mediation, or other resolution services.

## What the certificate records

- A declarant's statement, with or without evidence.
- The declared identity mode and the assurance level actually established.
- Relevant Bitcoin context, such as transaction IDs, addresses, network, service, and event dates, when supplied.
- Jurisdictions and proceedings as declared, documented, or formally recognized; these statuses must never be conflated.
- Evidence manifests and integrity digests. Sensitive files are stored encrypted and access-controlled, not published as plaintext.
- Institution acknowledgements, responses, legal-contact requests, expert reports, mediation events, and resolution outcomes as separate append-only events.
- References to external resolution services and their participation rules.

## Product boundaries

BICDN certifies the integrity, origin under a stated key/trust policy, registration time where supported, and history of submitted records. A valid signature or timestamp does **not** establish that an allegation is true, that evidence is admissible, that an identity is a verified civil identity, or that a court has jurisdiction. Anonymous contributions are recorded as anonymous submissions and are not automatically verified evidence.

BICDN is an integration layer for existing institutions. An institution retains control of its own procedure and legal decisions; it may add signed acknowledgements and responses to the BICDN case history without controlling or deleting the declarant's original record.

## Main capabilities

1. **Declaration form:** structured case intake, optional evidence, consent and visibility choices.
2. **Certificate issuance:** canonicalized claims, issuer signature, unique identifier, timestamps and verification metadata.
3. **Distributed propagation:** event replication and reconciliation across authorized nodes; content-addressed storage may be used for encrypted objects.
4. **Anonymous contributions:** separate submissions linked to a case without requiring a public identity; privacy limitations and abuse controls are documented.
5. **Jurisdiction registry:** multi-jurisdiction relationships with explicit status and source.
6. **Institutional gateway:** APIs and portable references for existing company and legal workflows.
7. **Legal Contact Protocol:** confidential request to communicate through participating lawyers, with a restricted encrypted message channel.
8. **External Conflict Resolution Access:** discovery/access to independent technical experts, consensus panels, mediators, and—only where agreed and legally appropriate—arbitration providers.

## Lifecycle

`DRAFT → SUBMITTED → ISSUED → PROPAGATING → OPEN → UNDER_REVIEW → RESOLUTION_IN_PROGRESS → RESOLVED | UNRESOLVED | CLOSED`

These are case lifecycle labels, not legal findings. Events are appended; corrections supersede or annotate earlier events rather than silently rewriting them. A case can be reopened by a new event where policy permits.

## Files

- [Service specification](./SERVICE-SPECIFICATION.md)
- [Form and case-event JSON Schema](./bicdn-case.schema.json)
- [Contribution JSON Schema](./bicdn-contribution.schema.json)
- [Legal-contact contribution example](./examples/anonymous-legal-contact-request.json)
- [Evidence and testing guide](./EVIDENCE-AND-TESTING.md)
- [Test traceability](./TEST-TRACEABILITY.md)

## Implementation status

This addition defines a proposed product and data contract. It does not add a new identifier to the existing node-identity certificate allowlist, does not issue live certificates, does not implement a production anonymous submission service, does not establish IPFS pinning/retention, and does not provide a live legal or dispute-resolution service. Those require separate implementation, threat modelling, privacy review, tests, issuer governance, and institutional agreements.

The BICDN case certificate is an application-level document/case credential. It must remain distinct from the existing Node Core OS node-identity certificate envelope.
