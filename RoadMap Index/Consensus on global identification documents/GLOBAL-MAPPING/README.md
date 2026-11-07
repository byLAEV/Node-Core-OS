# Global Mapping — From World to Issuing Institution

## Mission

Build the worldwide institutional and geographic database that supports the broader Node Core OS byLAEV global identity objective.

The project has two connected goals:

1. Define a persistent network identity credential — provisionally named **Node Core Global Identity Document (NC-GID)** — that can identify a person within Node Core OS and associate that person with one or more network nodes, including when the person has no official identity document or their nationality is not yet established.
2. Map the countries, jurisdictions, competent authorities, legal procedures, and authorized organizations that may help verify civil identity, register civil events, issue identity documents, determine nationality, or process relevant immigration, protection, and statelessness matters.

The global mapping is a research and planning resource. It does not imply that an institution has agreed to connect, that an API exists, that a person qualifies for a legal status, or that a Node Core OS connector is implemented.

NC-GID would be a credential for identity continuity inside the Node Core OS network. It would not itself be a passport, national identity card, proof of citizenship, or grant of nationality. Nationality and the legal validity of state documents remain decisions of competent authorities under applicable law.

## Macro-to-micro hierarchy

“Macro to micro” means mapping the complete pathway from a worldwide identity layer to the individual person and the institutions that may assess their case. The database must support both global-to-individual discovery and individual-to-institution routing.

`WORLD → CONTINENT / REGION → COUNTRY OR AREA → SUBNATIONAL JURISDICTION → COMPETENT INSTITUTION / AUTHORIZED ORGANIZATION → PROCEDURE, DOCUMENT OR SERVICE → API / CONNECTOR → PERSON + NODE`

### Level 0 — World: global identity layer

Define the global NC-GID model, the shared identity and evidence rules, the worldwide jurisdiction index, and common institutional-interoperability standards. The global layer must not presume that everyone has a nationality or official document.

### Level 1 — Continents and geographic regions

Create a consistent continental and regional index for research coverage, regional organization, and future interoperability. Use the United Nations Statistics Division M49 classification for standardized region and country/area indexing: https://unstats.un.org/unsd/methodology/m49/

M49 is a statistical geographic classification. It is not a legal statement about sovereignty, borders, citizenship, or an institution's authority. The project may display the familiar seven-continent model for navigation while retaining M49 region and subregion codes for consistent data organization.

### Level 2 — Countries and areas

Enumerate countries and areas within each region using the selected reference dataset. Record ISO 3166 codes where applicable, M49 codes, official names, and source dates. Keep territories and other areas distinguishable from sovereign states; do not silently classify them as countries.

For each country or area, research the relevant legal framework and official procedures for civil registration, nationality, identity documents, passports, residence, immigration, asylum, refugee protection, and statelessness where applicable.

### Level 3 — Subnational jurisdictions

Where institutional responsibilities or legal procedures are decentralized, record the relevant state, province, territory, autonomous region, municipality, or other administrative unit. Do not create empty administrative layers when they are not relevant.

### Level 4 — Competent institutions and authorized organizations

Map institutions by their actual legal mandate and function. The database must go beyond national ID and passport issuers and, where applicable, include:

- Civil and birth registration authorities.
- Nationality, citizenship, and naturalization authorities.
- National identity-card issuers and passport authorities.
- Immigration and residence authorities.
- Asylum and refugee-protection authorities.
- Statelessness determination bodies or official procedures.
- Courts, ombuds institutions, or administrative review bodies with a relevant legal role.
- UN agencies, humanitarian organizations, legal-aid providers, and civil-society organizations that provide authorized support or referrals.

Clearly distinguish government decision-makers from service providers, contractors, NGOs, and support organizations. Do not attribute the power to grant nationality or issue state documents to an organization that does not legally hold that power.

### Level 5 — Procedures, documents, and services

Record each relevant document family, official procedure, verification service, or authorized referral channel separately. For each one, identify eligibility requirements, evidence requirements, competent authority, official source, submission method, and known limitations. A possible legal pathway is a research lead, not a guarantee that a person qualifies or that an application will be accepted.

### Level 6 — API and connector mapping

Record two distinct integration sides:

1. **Institution-provided interface:** the official API, signed credential mechanism, verification gateway, service portal, application channel, or other official procedure offered by the institution.
2. **Node Core OS API/connector:** the Node Core OS capability or connector intended to communicate with that institution after the project specifies and implements it.

Never place an invented URL or endpoint in either field. If the information is not confirmed, use an explicit status such as `UNKNOWN`, `NOT_PUBLISHED`, `RESTRICTED`, or `NOT_APPLICABLE`. A public website or contact form is not automatically an API.

### Level 7 — Person and Node Core OS node

Associate the person with a persistent NC-GID and a technical node identity. Record declarations and evidence with provenance and appropriate protection; identify possible jurisdictional links; and support lawful referrals or applications to competent institutions. The node identifier is a technical reference, not proof of civil identity or nationality.

The database must distinguish a person who lacks documents from a person whose nationality is undetermined and from a person whose statelessness has been formally recognized. Node Core OS must not independently assign nationality or determine statelessness. A competent authority makes legal determinations under its applicable procedure.

## Individual-to-institution pathway

The mapping must make it possible to follow a person's case without treating network consensus as a substitute for legal authority:

1. Establish a Node Core OS network identity (NC-GID) without presuming nationality.
2. Record self-declared information and available evidence with source, date, provenance, and appropriate authorization.
3. Identify possible links to jurisdictions through evidence such as birth, parentage, residence, family records, or previous documents.
4. Identify the competent authorities and official procedures for the relevant jurisdictions.
5. Provide the authorized application or referral path, or use an institutional API only when access is permitted.
6. Record official responses and decisions with verifiable provenance.
7. Link any subsequently confirmed nationality or state-issued document to the NC-GID without replacing the authoritative institutional record.

Consensus may validate the integrity and provenance of network records. It cannot turn an unverified claim into an institutional confirmation or a legal determination.

## Privacy and evidence boundary

The public mapping database contains institutional, geographic, and procedural information — not people's identity documents or personal case files. Never place real identity documents, biometric data, personal identifiers, or sensitive case evidence in public mapping files, public IPFS gateways, or public ledgers.

Any future processing of personal evidence must have a lawful basis and apply data minimization, encryption, access control, retention limits, and appropriate consent or other authorization. Public hashes of predictable personal identifiers are not adequate privacy protection. Use synthetic data during early design and testing.

## Research workflow

1. Establish the geographic index and coverage rules.
2. Populate countries and areas under each geographic region.
3. Research the competent identity-document and passport authorities in each jurisdiction.
4. Confirm mandates using official legislation, government pages, or institutional sources.
5. Discover APIs and alternative official verification mechanisms.
6. Record authentication, permissions, legal agreements, eligibility, costs, rate limits, and data-access restrictions.
7. Map each institutional requirement to a Node Core OS API capability.
8. Design common schemas and connector interfaces.
9. Test connectors with fictitious data and authorized sandbox environments.
10. Conduct real institutional integration only after the required authorization is obtained.
11. Revisit records periodically and update their sources and review dates.

## Evidence and status rules

Every factual field should have a source URL, source type, date checked, and confidence or evidence status. Prefer primary official sources. Secondary sources may help discover an institution but should not be the sole evidence for legal authority or API availability.

Use the following research lifecycle:

- `NOT_RESEARCHED`
- `RESEARCH_IN_PROGRESS`
- `INSTITUTION_IDENTIFIED`
- `AUTHORITY_CONFIRMED`
- `API_OR_MECHANISM_RESEARCHED`
- `ACCESS_REQUIREMENTS_CONFIRMED`
- `CONNECTOR_SPECIFIED`
- `SANDBOX_TESTED`
- `AUTHORIZED_INTEGRATION_VALIDATED`
- `NOT_AVAILABLE`
- `BLOCKED`

Do not confuse these states. An institution may be confirmed while its API remains unknown. An API may be documented but restricted. A connector may be implemented but not authorized for production use.

## Registers and templates

- [Continental and Geographic Region Index](CONTINENT-INDEX.md)
- [Country and Jurisdiction Register](COUNTRY-AND-JURISDICTION-REGISTER.csv)
- [Issuer and API Register](ISSUER-AND-API-REGISTER.csv)
- [Institution Research Template](INSTITUTION-RESEARCH-TEMPLATE.md)
- [Node Core OS API Capability Catalogue](NODE-CORE-OS-API-CATALOG.md)

## Data quality requirements

- One institution per issuer record; do not combine unrelated authorities into one row.
- One document family per document record where responsibilities or verification differ.
- Preserve original official institution names and add English translations separately.
- Record the legal mandate and the actual operational service separately.
- Store direct links to API documentation, developer portals, sandbox pages, and access procedures where available.
- Record whether the API is public, partner-only, government-only, private, unavailable, or not yet confirmed.
- Never treat a website contact form as an API.
- Never infer that an API permits individual document-number lookups.
- Never store real identity documents or personal identifiers in public mapping files.
- Never publish personal data or identity-document images to IPFS or another public distributed store.

## Completion principle

The global map is complete only when its coverage is explicit, each jurisdiction has a documented research status, each identified issuer has source-backed records, and API availability and access conditions are classified honestly. Global coverage does not require every institution to expose an API; it requires the project to document what is actually available and what lawful integration path, if any, exists.


## Current geographic inventory baseline

The initial geographic register has been populated with **248 M49 country-or-area records**, grouped into the project's seven-continent navigation structure. This includes territories and other areas, not only sovereign states. Antarctica is retained as a geographic reference and is excluded from issuer research as a national jurisdiction.

| Continent navigation group | M49 records |
|---|---:|
| Africa | 60 |
| Asia | 50 |
| Europe | 51 |
| North America (including Central America and the Caribbean) | 41 |
| South America | 16 |
| Oceania | 29 |
| Antarctica (geographic reference only) | 1 |
| **Total** | **248** |

Read the [complete country and area list by continent](COUNTRIES-AND-AREAS-BY-CONTINENT.md), the [continent index](CONTINENT-INDEX.md), and the [structured CSV register](COUNTRY-AND-JURISDICTION-REGISTER.csv).

The country/area names, M49 codes, and ISO codes are based on the [UN Statistics Division M49 overview](https://unstats.un.org/unsd/methodology/m49/overview/). The CSV records the source and review date. The seven-continent navigation grouping is a project presentation layer; the original M49 region and subregion identifiers are preserved.

**Important status distinction:** geographic enumeration is populated, but identity issuer and passport issuer research remains `NOT_RESEARCHED` for the listed records. The 248 entries do not mean 248 institutions have been identified, nor that 248 API connections exist. The next phase is institution-by-institution research using official sources.


## Institutional research progress — Africa

The first African issuer research batch is recorded in [AFRICA-ISSUER-RESEARCH.md](AFRICA-ISSUER-RESEARCH.md). It covers 11 jurisdictions and adds 22 issuer records (one identity-document authority record and one passport-authority record per jurisdiction) to the master [ISSUER-AND-API-REGISTER.csv](ISSUER-AND-API-REGISTER.csv).

Africa has 60 M49 country-or-area records in the geographic baseline. Thirteen have received an institutional research pass; 47 remain to be researched. This is research coverage only, not API or integration coverage.

The strongest integration leads identified so far are:
- Ethiopia's Fayda authentication API, with OAuth 2.0/OIDC and organization partner onboarding.
- Ghana's NIA institutional identity-verification service, which requires formal onboarding and a service contract.
- South Africa's DHA National Population Register verification service for government and private-sector clients; public API details still require confirmation.

Continue country by country and preserve the difference between a public API, a restricted institutional service, a citizen application portal, and a contact channel.



## Expanded institutional and lawful-pathway database

The original `ISSUER-AND-API-REGISTER.csv` remains the source of truth for identity-document and passport issuer records. A second, broader register has now been added so the worldwide mapping can include institutions that register civil events, administer nationality and citizenship procedures, or provide asylum, refugee protection, and related services.

### New working files

- [Institution and Lawful Pathway Register](INSTITUTION-AND-PATHWAY-REGISTER.csv) — one record per institution or legally distinct institutional role, including mandate, authority level, jurisdiction, official service, API status, source evidence, and review notes.
- [Institution Relationship Register](INSTITUTION-RELATIONSHIP-REGISTER.csv) — explicit institutional hierarchy, referral, and transition relationships.
- [Mapping Coverage Register](MAPPING-COVERAGE-REGISTER.csv) — one row for each of the 248 geographic records, with function-by-function mapping status.
- [Africa Institution and Pathway Research — Batch 02 (Senegal)](AFRICA-INSTITUTION-AND-PATHWAY-RESEARCH-BATCH-02-SENEGAL.md) — legal and institutional map for refugee/stateless recognition and related documents.
- [Institution and Pathway Research Template](INSTITUTION-AND-PATHWAY-RESEARCH-TEMPLATE.md) — reusable research record with mandatory distinctions and safeguards.
- [Africa Institution and Pathway Research — Batch 01](AFRICA-INSTITUTION-AND-PATHWAY-RESEARCH-BATCH-01.md) — first expanded institutional batch across 11 African jurisdictions.

### First expanded research batch

The first batch contains **33 institution/role records across 11 African jurisdictions**: South Africa, Ghana, Nigeria, Kenya, Uganda, Rwanda, Ethiopia, Botswana, Zambia, Namibia, and the United Republic of Tanzania.

It supplements the existing identity-document and passport research. The new records cover civil registration, nationality/citizenship administration, identity registration, immigration, asylum and refugee protection, and selected subnational civil-registration functions.

This is a partial research batch, not full African or global coverage. Some roles are explicitly marked as pending primary-source confirmation or further legal review. The database must preserve those statuses instead of upgrading uncertain findings to confirmed facts.

### Mandatory data distinctions

- Civil/birth registration records a vital event; it does not automatically grant nationality.
- A person without identity documents is not automatically stateless.
- Nationality, immigration/residence status, refugee status, and possession of an identity document are separate legal concepts.
- A protection agency, secretariat, or support organization is not automatically the legal decision-maker for nationality or refugee status.
- An online application portal or certificate-verification form is not automatically an API.
- No public personal case data, identity documents, biometrics, or personal identifiers belong in these mapping files or public distributed storage.

### Next research priorities

1. Continue the African country/area inventory beyond the first 11 jurisdictions.
2. Resolve every record marked as pending primary-source confirmation or legal review.
3. Identify competent statelessness determination or protection procedures where they exist; do not infer them from the existence of a refugee agency.
4. Extend the same institutional categories to Asia, Europe, the Americas, and Oceania.
5. Only after the institutional roles and procedures are reliably mapped, define the corresponding Node Core OS data schemas, APIs, and authorized connectors.


## Versioned data model and validation

The mapping now has a versioned normalized target model and an initial lawful-procedure register. These files establish the structure for future database/API work; they do not claim that Node Core OS has deployed an identity case-management service or connected to a government API.

- [Global Identity Data Model v1.0](GLOBAL-IDENTITY-DATA-MODEL-v1.md) — entity relationships, stable identifiers, legal distinctions, privacy boundaries, and versioning policy.
- [JSON Schema](global-identity-data-model.schema.json) — normalized target contract for jurisdiction, institution, issuer, procedure, and evidence-source records.
- [Lawful Identity Pathway Register](LAWFUL-IDENTITY-PATHWAY-REGISTER.csv) — first seven procedure research records, with unresolved legal questions explicitly marked.
- [Mapping validator](validate_global_mapping.py) — dependency-free CSV structure, jurisdiction reference, source URL, date, and foreign-key checks.
- [Validator tests](test_validate_global_mapping.py) — unit tests for URL handling and quoted CSV parsing.

### Cross-references and current coverage

The 29 national-ID, passport, refugee and stateless-person document issuer rows now each link to an `institution_record_id`. The institution register now has 47 records across 13 African jurisdictions. Three additional institution records close issuer-directory gaps for Ghana's Passport Office, Ethiopia's National ID Program, and Tanzania's National Identification Authority.

The lawful-procedure register currently contains thirteen researched starting points. It is intentionally incomplete: the decision-maker, appeals route, eligibility rules, and supporting evidence must be confirmed from current primary law before any case-routing logic is built.

### Controlled implementation sequence

1. Keep the public CSV mapping free of personal data.
2. Validate structural and referential integrity before every research batch.
3. Normalize legacy status values to the controlled vocabulary in the JSON Schema; preserve raw source values and review notes.
4. Expand institution and procedure coverage across all African M49 records.
5. Specify Node Core OS APIs and connectors only after the institution's role, procedure, legal basis, access conditions, and technical interface are confirmed.
6. Test with synthetic records, including low-bandwidth, timeout, retry, idempotency, and manual fallback scenarios.


## Institutional mapping progress — Senegal (Africa Batch 02)

The Africa institutional map has expanded to **13 of 60 M49 country-or-area records**. Senegal and Egypt extend the institutional map beyond the initial eleven-country batch. Senegal adds six institutional roles, four document records and four legal pathways; Egypt adds five institutional roles, three document records and two procedure records. See [Africa Batch 02 — Senegal](AFRICA-INSTITUTION-AND-PATHWAY-RESEARCH-BATCH-02-SENEGAL.md) and [Africa Batch 03 — Egypt](AFRICA-INSTITUTION-AND-PATHWAY-RESEARCH-BATCH-03-EGYPT.md).

The key legal finding is that Senegal has a statutory admission procedure for both refugee and stateless-person status. Decree No. 2025-1559 defines the procedure, places intake and review with the CNGRA, provides an appeal route, and states that status is granted by decree. Decree No. 2025-1560 assigns issuance of biometric identity and travel documents for recognized refugees and stateless persons to the Ministry of the Interior and Public Security, under CNGRA coordination.

This is a country-specific state pathway, not a global identity document and not a mechanism for Node Core OS to grant citizenship. It is an institutional pathway that the future NC-GID may reference, subject to consent and lawful access. The public mapping contains no personal case data.

The [Mapping Coverage Register](MAPPING-COVERAGE-REGISTER.csv) contains 248 geographic rows. It marks the twelve researched African jurisdictions as partially mapped and keeps all other unresearched jurisdictions explicitly open. Functional categories with no mapped record are marked NOT_RESEARCHED, not presumed nonexistent. The API/connector layer remains deferred.



**Senegal operational note:** the Ministry announced on 24 September 2026 that renewal operations for CEDEAO biometric identity cards issued from 4 October to 31 December 2016 would start on 25 September 2026. This is a limited renewal cohort and does not prove that all issuance services are fully restored. Source: https://interieur.gouv.sn/actualites/communiques/renouvellement-cartes-identite-biometriques-cedeao-demarrage-25-septembre-2026


### Egypt — institutional mapping update

Egypt has five institution records covering the Civil Status Sector, PENA, the Ministry of Foreign Affairs, the statutory Permanent Committee for Refugee Affairs and UNHCR Egypt's current transitional operation. The issuer register adds Egyptian national ID, ordinary passport and refugee documentation records; the procedure register adds nationality service routes and the asylum transition. The Committee's statutory authority is established by Asylum Law No. 164/2024, but UNHCR reports that it continues refugee registration, documentation and status determination until the national system is fully operational. The handover therefore remains an explicit verification item, not an assumed completed transition. See [Egypt Batch 03](AFRICA-INSTITUTION-AND-PATHWAY-RESEARCH-BATCH-03-EGYPT.md).


## Mission and completion requirements

The purpose, person-centred use cases, institutional hierarchy, evidence-to-institution pathway, trust boundaries, source policy, API sequencing and completion criteria for this work are defined in [Global Mapping Mission and Requirements](GLOBAL-MAPPING-MISSION-AND-REQUIREMENTS.md). This document governs the mapping phase: institutional and legal cartography first; API and connector implementation later.


**Egypt classification correction:** all five Egyptian institution records use the Africa navigation group, consistent with the M49 geographic register (region 002). The 2026 asylum executive regulations provide a staged UNHCR-to-government transition; the handover is not treated as complete. See the official regulation text in Egypt Batch 03.
