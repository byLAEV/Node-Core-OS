# Evidence and Testing — BICDN-01

**Profile:** `bitcoin-conflict-declaration`  
**Status:** proposed specification; implementation evidence not yet established.

## Evidence categories

1. **Declarant assertion:** information supplied by the person or organization completing the form.
2. **Cryptographic integrity:** signature/hash verification for the exact bytes or canonical claims.
3. **Source provenance:** information about who submitted an item and how it entered the system; anonymous ingress may provide only limited provenance.
4. **Independent corroboration:** separate evidence or review supporting an assertion.
5. **Institutional record:** a signed receipt, response, referral, or decision from an identified institution.
6. **Expert or resolution report:** a signed report stating method, scope, participants, conflicts, dissent, and limitations.

These categories must not be conflated. A valid certificate confirms only the claims and checks stated by its issuer. It does not prove the truth of a declaration.

## Required test groups

- **Schema:** required fields, optional evidence, invalid enum values, additional properties, malformed references, bounds, and Unicode.
- **Canonicalization/signing:** deterministic canonical bytes, valid signature, tampered payload, unknown issuer, key rotation and revocation.
- **Case ledger:** append-only semantics, duplicate event IDs, event-link integrity, correction events, concurrent event ordering, replay protection.
- **Anonymous intake:** no required public identity field, spam controls, rate limits, metadata minimization, privacy leakage review, abuse handling.
- **Confidentiality:** encryption before storage, access denial, key rotation/revocation, secure message channel, no plaintext leakage in logs or public views.
- **Jurisdiction:** declared/documented/recognized distinction, country code validation, source references, no automatic legal-competence conclusion.
- **Institutional integration:** independently signed receipt, response, internal case reference, access grant and revocation.
- **Resolution:** participant identity/role, conflict-of-interest declarations, method, dissent, voluntary mediation, arbitration consent checks.
- **Distributed sync:** two-node and multi-node replication, idempotency, out-of-order events, concurrent additions, offline recovery, missing blocks and pinning failures.
- **Retention/recovery:** backup, retention schedule, legal hold, deletion of controlled copies where required, cryptographic erasure limits, key recovery and node loss.

## Safe test fixtures

Use synthetic identities, fictional companies, testnet-like transaction identifiers clearly marked as fixtures, and fabricated jurisdictions/case numbers. Never put real personal data, real private keys, seed phrases, or unredacted legal documents in tests or public repository files.

## Evidence record

Record test ID, commit SHA, environment, command, dependencies, expected and observed result, artifact digest, workflow URL, reviewer, known limitations, and whether the run tests schema, format, component behavior, or product effectiveness.

## Current evidence boundary

This repository change adds documentation and schemas only. Until executable validators, issuance code, distributed synchronization, anonymous ingress, encrypted evidence storage, institutional adapters, and their tests exist and pass, the product remains **proposed / not implemented**. A schema that validates a JSON object is not evidence that a network service operates securely.
