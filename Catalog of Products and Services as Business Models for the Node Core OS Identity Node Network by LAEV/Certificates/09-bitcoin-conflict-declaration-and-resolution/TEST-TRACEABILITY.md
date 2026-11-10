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
- `tests/test_bicdn_schemas.py`: executable JSON Schema contract tests for schema validity, valid case/contribution fixtures, rejection of missing encrypted references for restricted/private content, and rejection of undeclared fields.
- `EVIDENCE-AND-TESTING.md`: required test groups and evidence boundaries.

## Existing implementation evidence

BICDN-specific JSON Schema contract tests now exist in `tests/test_bicdn_schemas.py`. They validate the Draft 2020-12 schemas, the synthetic anonymous legal-contact example, required encrypted references for restricted/private content, and rejection of undeclared case properties. The certificate-catalog CI workflow runs these tests alongside the separate Node Core OS identity certificate-envelope tests.

These schema tests validate data contracts only. They do not implement or prove BICDN issuance, signatures, anonymous ingress, encrypted evidence storage, a legal gateway, institutional adapters, or a distributed case ledger. Existing Node Core OS identity certificate tests cover a separate certificate envelope and must not be presented as BICDN credential-signing evidence.

## Required next tests

1. Add canonical signing and issuer-verification tests for the application-level BICDN credential.
2. Add append-only ledger, event-link, replay, and correction-event tests.
3. Add anonymous intake privacy, abuse-control, and metadata-leakage tests.
4. Add encryption/access-control tests against an actual storage implementation for restricted messages and evidence.
5. Add jurisdiction-status validation and no-inference tests beyond JSON enum validation.
6. Add institution receipt/response signature tests.
7. Add multi-node idempotent synchronization and conflict-reconciliation tests.
8. Add legal-contact and external-resolution workflow tests with synthetic participants.

## CI acceptance

Create a dedicated BICDN workflow only after executable tests exist. It must run on pull requests and pushes affecting this directory, schemas, implementation, and tests. Report exact commit, commands, test count, result, and limitations. Do not call documentation integrity a security or legal certification.
