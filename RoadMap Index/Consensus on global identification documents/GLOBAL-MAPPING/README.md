# Global Mapping — From World to Issuing Institution

## Mission

Build a structured, source-backed inventory of the authorities and institutions that issue personal identification documents and passports worldwide. This mapping will provide the research foundation for designing Node Core OS byLAEV APIs and institution-specific connectors.

The mapping is a research and planning resource. It does not imply that an institution has agreed to connect, that an API exists, or that a Node Core OS connector is implemented.

## Macro-to-micro hierarchy

The mapping must follow this hierarchy:

`WORLD → CONTINENT / GEOGRAPHIC REGION → COUNTRY OR AREA → SUBNATIONAL JURISDICTION → ISSUING INSTITUTION → DOCUMENT TYPE → INSTITUTION API / NODE CORE OS CONNECTOR`

### Level 0 — World

Define the complete intended coverage of the global Node Core OS identity-document network.

### Level 1 — Continents and geographic regions

Create a consistent geographic index. Use the United Nations Statistics Division M49 classification for standardized region and country/area indexing: https://unstats.un.org/unsd/methodology/m49/

M49 is a statistical geographic classification. It is not a legal statement about sovereignty, borders, citizenship, or an institution's authority. The project may display the familiar seven-continent model for navigation while retaining M49 region and subregion codes for consistent data organization.

### Level 2 — Countries and areas

Enumerate countries and areas within each region using the selected reference dataset. Record ISO 3166 codes where applicable, M49 codes, official names, and source dates. Keep territories and other areas distinguishable from sovereign states; do not silently classify them as countries.

### Level 3 — Subnational jurisdictions

Where identity-document or passport responsibilities are decentralized, record the relevant state, province, territory, autonomous region, or other administrative unit. Do not create empty administrative layers when they are not relevant.

### Level 4 — Issuing institutions

Identify the legally competent authority for each document family. Separate the legal issuer from service operators, contractors, manufacturers, personalization providers, and technology vendors.

### Level 5 — Documents and verification services

Record each document category separately: national identity card, passport, civil registration credential, electronic identity credential, residence document, and other officially recognized identity documents within scope.

For each document type, identify the official verification service or mechanism, if one exists.

### Level 6 — API and connector mapping

Record two distinct integration sides:

1. **Institution-provided API/service:** the official API, service portal, signed credential mechanism, verification gateway, or other official mechanism provided by the institution.
2. **Node Core OS API/connector:** the Node Core OS endpoint or connector that will communicate with that institution after the project specifies and implements it.

Never place an invented URL or endpoint in either field. If the information is not confirmed, use an explicit status such as `UNKNOWN`, `NOT_PUBLISHED`, `RESTRICTED`, or `NOT_APPLICABLE`.

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
