# Global Mapping — Identity and Passport Issuer Directory

**Project:** Node Core OS byLAEV  
**Primary objective:** identify, for every country, territory or relevant jurisdiction, the public authority responsible for issuing identity documents and the authority responsible for issuing passports or state travel documents.

## What this mapping must cover

1. All seven continental navigation groups: Africa, Asia, Europe, North America, South America, Oceania and Antarctica as a geographic reference.
2. Every country and area in the 248-record UN M49 geographic baseline. The baseline includes countries, territories and other areas; it is not a list of 248 sovereign states.
3. Special administrative regions, autonomous jurisdictions, dependencies and other areas where identity or passport issuance is handled by a distinct authority. These remain linked to their geographic parent and legal status.
4. Global, regional and non-territorial organizations that issue official identity or travel documents outside the ordinary national issuer structure. These are maintained in a separate register and are not counted as country-level passport issuers.

For every applicable jurisdiction, the minimum target is:
- The official name of the identity-document issuing authority, or an explicit evidence-based explanation of why it has no separate authority.
- The official website or the most direct official service page.
- The official name of the passport/travel-document issuing authority and its official web page.
- A source-backed status and a review date.

An identity-card issuer, civil registry, nationality authority and passport authority are not automatically the same institution. The register records the authority responsible for the document, not simply a ministry that is related to the subject.

## Canonical registers

- [Global Identity and Passport Issuer Master Register](GLOBAL-IDENTITY-AND-PASSPORT-ISSUER-MASTER-REGISTER.csv) — one row per geographic country/area record, joining the authority names and official websites.
- [Issuer and API Register](ISSUER-AND-API-REGISTER.csv) — detailed records for each document family and issuing institution. API fields are retained for future work; API research is not the current completion requirement.
- [Extra-continental and Regional Document Issuers](EXTRACONTINENTAL-AND-REGIONAL-DOCUMENT-ISSUERS.csv) — global, regional and non-territorial issuers of restricted official travel documents, kept separate from national passports.
- [Country and Jurisdiction Register](COUNTRY-AND-JURISDICTION-REGISTER.csv) — canonical geographic baseline and M49/ISO cross-references.
- [Mapping Coverage Register](MAPPING-COVERAGE-REGISTER.csv) — supporting coverage view. It also retains broader institutional-domain fields for later phases.
- [Issuer Mapping Scope and Coverage Rules](ISSUER-MAPPING-SCOPE-AND-COVERAGE.md) — definitions, status meanings and completion rules.
- [Continental and Geographic Region Index](CONTINENT-INDEX.md) — continental navigation and regional coverage.

## Current issuer-directory coverage

The geographic baseline contains **248 records**: **247 country/area jurisdictions** plus Antarctica as a geographic reference only.

As of 2026-11-06, **16 of 247 applicable country/area jurisdictions** have both an identity-document issuer and a passport issuer recorded in the detailed issuer register. This is an issuer-directory measure only; it is not a measure of full institutional, legal-procedure or API coverage.

| Continental group | M49 records | Both issuer categories identified |
|---|---:|---:|
| Africa | 60 | 14 |
| Asia | 50 | 2 |
| Europe | 51 | 0 |
| North America (including Central America and the Caribbean) | 41 | 0 |
| South America | 16 | 0 |
| Oceania | 29 | 0 |
| Antarctica | 1 geographic reference | Not applicable |
 
The current identified issuer set includes the initial 14 jurisdictions represented in the African issuer register, plus the separately administered Hong Kong and Macao SAR issuer authorities. Every record remains subject to ongoing source review.

## Separate treatment of special issuers

Hong Kong and Macao are included in the M49 baseline as separate areas and have their own SAR identity/passport services. They are therefore recorded as separate jurisdiction rows while preserving the M49 names and codes.

The extra-continental/regional register includes examples of official travel-document issuers such as the Sovereign Military Order of Malta, the European Union and the United Nations. These documents have limited institutional eligibility and are **not equivalent to ordinary national passports or public identity cards**. They are deliberately excluded from the country-level coverage denominator.

## Status and evidence rules

- `AUTHORITY_IDENTIFIED`: the named issuing authority is recorded with an official source.
- `RESEARCH_IN_PROGRESS`: some research exists, but the relevant issuer has not yet been recorded to the required standard.
- `NOT_RESEARCHED`: no issuer research is recorded. This does not mean that no authority exists.
- `NOT_APPLICABLE`: the entry is a geographic reference or the document category is not applicable, supported by the scope of the record.
- `SOURCE_REVIEW_REQUIRED`: a source or mandate needs confirmation or updating.

Prefer government and issuer websites, current laws and official service directories. Do not infer the issuing authority from a private website, third-party travel site or an unverified search result. Record both document issuer and website even when one institution issues both document families.

## Deferred work

API discovery, authentication, contracts, connector implementation, migration/travel rules, nationality procedures and other institutional domains are later phases. A public website or online application portal is not automatically an API. No integration is implied by an issuer record.

The wider functional framework remains documented in [GLOBAL-FUNCTIONAL-DOMAIN-MAP.md](GLOBAL-FUNCTIONAL-DOMAIN-MAP.md), but it must not distract from completing the issuer directory first.

## Geographic reference

The 248-record baseline retains the UN Statistics Division M49 codes and ISO 3166 identifiers where available: https://unstats.un.org/unsd/methodology/m49/overview/. M49 is a statistical geographic classification, not a legal determination of sovereignty or of an issuer's authority.
