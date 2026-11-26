# Global Identity Data Model — Version 1.0

## Purpose and implementation boundary
This version defines the normalized target data contract for Node Core OS global institutional mapping. It is a research-data model, not a production identity system or legal decision engine. Existing CSV registers remain the maintained source records until a database migration is separately specified and tested.

## Entity relationships
`Jurisdiction → Institution → Procedure → EvidenceSource`

An issuer/document role is performed by an institution and links through `institution_record_id`. A Node Core OS connector is separate from an institution's own API or portal.

## Stable identifiers
- Jurisdiction: M49 country/area code, plus ISO alpha-2 where applicable.
- Institution: `institution_record_id`.
- Issuer role: `issuer_record_id`.
- Procedure: `procedure_record_id`.
- Connector: Node Core OS connector ID, only after specification.
- Evidence source: stable source ID, to be assigned during evidence normalization.

## Required legal distinctions
1. Nationality is not the same as a national identity number, residence, refugee status, or possession of a document.
2. Civil/birth registration records an event; it does not itself grant nationality.
3. A person without identity documents is not automatically stateless.
4. A self-declared fact is not an institution-verified fact.
5. A website, application portal, or web certificate check is not automatically an API.
6. Institution API status and Node Core OS connector status are independent.
7. A secretariat, contractor, or support organization is not a legal decision-maker unless a primary legal source confirms that role.

## Trust and evidence
Preserve who asserted a fact, which evidence was checked, which authority responded, the time and scope of the check, and limitations. Never silently promote a self-declared claim to corroborated, institution-verified, or legally recognized.

## Privacy and safety
- Public mapping files contain institutional metadata and public source URLs only.
- Never commit personal case data, real identity documents, biometrics, or personal identifiers.
- Use synthetic test subjects and opaque random identifiers in development.
- Do not put personal information, document numbers, biometrics, or reusable personal-data hashes on public IPFS or public blockchains.
- Any future personal-evidence service requires a separate encrypted, access-controlled, consent-aware storage and retention design.
- Do not infer nationality, statelessness, eligibility, or legal status from incomplete evidence.
- Design for low bandwidth: bounded retries, timeouts, idempotency, resumable transfer, and manual/offline fallback.

## Source-of-truth files
- `COUNTRY-AND-JURISDICTION-REGISTER.csv`: geographic index.
- `INSTITUTION-AND-PATHWAY-REGISTER.csv`: institution mandates and institutional research.
- `ISSUER-AND-API-REGISTER.csv`: identity/passport issuer roles; each row links to an institution.
- `LAWFUL-IDENTITY-PATHWAY-REGISTER.csv`: procedure research and unresolved legal questions.
- `global-identity-data-model.schema.json`: normalized target schema.
- `validate_global_mapping.py` and `test_validate_global_mapping.py`: dependency-free validation and tests.

Do not replace the source CSVs during migration. Normalize only after the mapping and validation process is reproducible.

## Versioning
Patch: non-breaking corrections. Minor: optional fields or new categories. Major: required-key or relationship semantics change. Preserve source URLs, research dates, previous values, and change rationale.
