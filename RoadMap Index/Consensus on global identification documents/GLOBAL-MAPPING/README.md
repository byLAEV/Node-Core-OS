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

Africa has 60 M49 country-or-area records in the geographic baseline. Eleven have received this first issuer-research pass; 49 remain to be researched. This is research coverage only, not API or integration coverage.

The strongest integration leads identified so far are:
- Ethiopia's Fayda authentication API, with OAuth 2.0/OIDC and organization partner onboarding.
- Ghana's NIA institutional identity-verification service, which requires formal onboarding and a service contract.
- South Africa's DHA National Population Register verification service for government and private-sector clients; public API details still require confirmation.

Continue country by country and preserve the difference between a public API, a restricted institutional service, a citizen application portal, and a contact channel.
