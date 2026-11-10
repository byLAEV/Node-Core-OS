# Test Traceability — BICDN-01

- **Product ID:** `BICDN-01`
- **Profile:** `bitcoin-conflict-declaration`
- **Version:** `0.1.0-draft`
- **Implementation classification:** **DOCUMENTATION AND SCHEMA PROPOSAL ONLY**
- **Production status:** **NOT IMPLEMENTED / NOT APPROVED**

## Added artifacts

- `README.md`: product purpose and boundaries.
- `SERVICE-SPECIFICATION.md`: actors, lifecycle, jurisdictions, anonymous contributions, legal contact, resolution access, institutional integration, storage and acceptance criteria.
- `bicdn-case.schema.json`: initial case declaration and certificate claims.
- `bicdn-contribution.schema.json`: append-only contribution event.
- `examples/anonymous-legal-contact-request.json`: synthetic example for the requested anonymous lawyer-contact contribution.
- `EVIDENCE-AND-TESTING.md`: required test groups and evidence boundaries.

## Existing implementation evidence

No BICDN-specific issuance, schema-validation, anonymous ingress, encrypted evidence store, legal gateway, institutional adapter, or distributed case ledger test was added by this documentation change. Existing Node Core OS identity certificate tests cover a separate certificate envelope and must not be presented as BICDN implementation evidence.

## Required next tests

1. Add JSON Schema validation tests for valid and invalid case/contribution fixtures.
2. Add canonical signing and issuer-verification tests for the application-level BICDN credential.
3. Add append-only ledger, event-link, replay, and correction-event tests.
4. Add anonymous intake privacy, abuse-control, and metadata-leakage tests.
5. Add encryption/access-control tests for restricted messages and evidence.
6. Add jurisdiction-status validation and no-inference tests.
7. Add institution receipt/response signature tests.
8. Add multi-node idempotent synchronization and conflict-reconciliation tests.
9. Add legal-contact and external-resolution workflow tests with synthetic participants.

## CI acceptance

Create a dedicated BICDN workflow only after executable tests exist. It must run on pull requests and pushes affecting this directory, schemas, implementation, and tests. Report exact commit, commands, test count, result, and limitations. Do not call documentation integrity a security or legal certification.
