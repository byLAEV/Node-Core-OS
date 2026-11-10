# Continental and Geographic Region Index

This index is the navigation layer for the worldwide identity-document and passport issuer directory.

## Geographic baseline

The project uses a seven-continent navigation model and preserves the UN Statistics Division M49 region, subregion, country/area code and ISO identifiers. The baseline contains **248 records**: 247 country/area jurisdictions and Antarctica as a geographic reference only.

Reference: https://unstats.un.org/unsd/methodology/m49/overview/

| Navigation ID | Continent / geographic scope | M49 records | Jurisdictions with both issuer categories identified | Notes |
|---|---|---:|---:|---|
| GEO-AF | Africa | 60 | 14 | 14 African jurisdictions currently have identity and passport issuer records. |
| GEO-AS | Asia | 50 | 2 | Includes the separately administered Hong Kong and Macao SAR issuer authorities. |
| GEO-EU | Europe | 51 | 0 | Issuer research remains pending across the M49 country/area baseline. |
| GEO-NA | North America | 41 | 0 | Includes Northern America, Central America and the Caribbean in the project's navigation grouping. |
| GEO-SA | South America | 16 | 0 | M49 South America grouping. |
| GEO-OC | Oceania | 29 | 0 | M49 Oceania grouping. |
| GEO-AN | Antarctica | 1 | Not applicable | Geographic reference only; not treated as a national issuer jurisdiction. |
| **TOTAL** | **World inventory** | **248** | **16** | The denominator for issuer coverage excludes the Antarctica reference: 247 applicable jurisdictions. |

## Navigation and source registers

- [Readable country and area list by continent](COUNTRIES-AND-AREAS-BY-CONTINENT.md)
- [Country and jurisdiction register](COUNTRY-AND-JURISDICTION-REGISTER.csv)
- [Global identity and passport issuer master register](GLOBAL-IDENTITY-AND-PASSPORT-ISSUER-MASTER-REGISTER.csv)
- [Extra-continental and regional document issuers](EXTRACONTINENTAL-AND-REGIONAL-DOCUMENT-ISSUERS.csv)

## Classification rules

M49 is a statistical geographic classification. It is not a legal determination of sovereignty, borders, nationality or institutional competence. A M49 country/area row can represent a territory or special administrative area rather than a sovereign State.

Special administrative regions and other areas with distinct issuing authorities must be represented separately and linked to their legal/geographic parent. Do not combine the Hong Kong SAR or Macao SAR issuing services with the PRC mainland issuer row.

Global, regional and non-territorial organizations that issue restricted official travel documents are recorded separately. They are not additional countries and must not be included in the 247-jurisdiction coverage denominator.

## Coverage interpretation

A jurisdiction counts as mapped for the core objective only when **both** an identity-document issuer and a passport issuer have been identified and linked to official sources. One mapped category does not complete the jurisdiction. `NOT_RESEARCHED` means that research is not yet recorded; it does not mean an authority does not exist.

The detailed scope and status definitions are in [ISSUER-MAPPING-SCOPE-AND-COVERAGE.md](ISSUER-MAPPING-SCOPE-AND-COVERAGE.md).
