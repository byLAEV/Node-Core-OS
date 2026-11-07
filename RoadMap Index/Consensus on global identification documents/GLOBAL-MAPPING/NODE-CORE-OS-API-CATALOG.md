# Node Core OS API Capability Catalogue

## Purpose

This catalogue will identify the API capabilities that Node Core OS byLAEV must design and expose to support institutional identity-document verification.

It is the Node Core OS side of the global mapping. It must be linked to institution records only after an API contract or connector specification exists.

## Capability register

| Capability ID | Intended responsibility | Required inputs (to be specified) | Expected output (to be specified) | Specification status |
|---|---|---|---|---|
| NCOS-ID-001 | Discover and retrieve issuer directory records. | Jurisdiction, issuer ID, document category. | Issuer metadata and source status. | NOT_SPECIFIED |
| NCOS-ID-002 | Register an institutional integration and its trust metadata. | Institution identity, authorization evidence, connector metadata. | Institutional integration record. | NOT_SPECIFIED |
| NCOS-ID-003 | Submit an authorized document verification request. | Request ID, issuer ID, document reference, purpose, authorization/consent context. | Accepted request or structured rejection. | NOT_SPECIFIED |
| NCOS-ID-004 | Receive and authenticate an institutional response. | Signed or authenticated response and request correlation data. | Validated response provenance and integrity result. | NOT_SPECIFIED |
| NCOS-ID-005 | Retrieve a verification record and its status. | Verification record ID and access authorization. | Status, checks performed, source, timestamp, limitations. | NOT_SPECIFIED |
| NCOS-ID-006 | Manage consent and authorization evidence. | Subject, purpose, relying party, requested checks, expiry. | Authorization decision and audit reference. | NOT_SPECIFIED |
| NCOS-ID-007 | Record identity association claims between node, person, document, and issuer. | Node reference, subject reference, document reference, issuer reference, evidence. | Association record with explicit verification state. | NOT_SPECIFIED |
| NCOS-ID-008 | Record revocation, expiry, correction, and status changes. | Record reference, authenticated event, reason, timestamp. | Updated status and audit trail. | NOT_SPECIFIED |
| NCOS-ID-009 | Expose connector health and integration status. | Connector ID and authorized diagnostic request. | Operational status without exposing personal data. | NOT_SPECIFIED |
| NCOS-ID-010 | Publish auditable consensus evidence for identity-association records. | Validated claim, verification provenance, consensus protocol data. | Consensus record that preserves issuer attestation boundaries. | NOT_SPECIFIED |

## API contract requirements

Before implementation, each capability must define:

- Stable versioned endpoint and HTTP method or alternative protocol operation.
- Request and response schemas.
- Authentication and authorization.
- Data minimization and purpose restrictions.
- Error codes and retry behavior.
- Idempotency and replay protection.
- Timeouts and low-bandwidth behavior.
- Audit and provenance requirements.
- Compatibility and deprecation policy.
- Unit, integration, security, and interoperability tests.

## Critical separation

The Node Core OS API is not the same as an institution's API. The institution controls its own service, access policy, data, and authoritative response. Node Core OS controls its own network interface, connector behavior, records, and consensus rules.

A Node Core OS endpoint must not be entered into the global issuer register as operational until its specification and implementation are verified. A connector must not be marked production-ready without the institution's required authorization.
