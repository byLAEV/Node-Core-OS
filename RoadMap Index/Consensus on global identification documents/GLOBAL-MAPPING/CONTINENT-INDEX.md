# Continental and Geographic Region Index

This index is the top-level navigation layer for the global issuer map.

## Geographic organization

The project uses a seven-continent navigation model and preserves the standardized region, subregion, M49 country-or-area code, and ISO identifiers from the United Nations Statistics Division M49 classification.

Reference: https://unstats.un.org/unsd/methodology/m49/overview/

The current baseline contains **248 M49 country-or-area records**. This is not a count of 248 sovereign states: M49 includes countries, territories, and other areas. Antarctica is included as a geographic reference only and is not treated as a national identity-document issuing jurisdiction.

| Navigation ID | Continent / geographic scope | M49 records | Mapping notes | Geographic inventory status | Issuer research status |
|---|---|---:|---|---|---|
| GEO-AF | Africa | 60 | M49 region 002. | POPULATED | PARTIALLY_RESEARCHED (12 of 60 M49 records) |
| GEO-AS | Asia | 50 | M49 region 142. | POPULATED | NOT_RESEARCHED |
| GEO-EU | Europe | 51 | M49 region 150. | POPULATED | NOT_RESEARCHED |
| GEO-NA | North America | 41 | Includes M49 Northern America, Central America, and the Caribbean. | POPULATED | NOT_RESEARCHED |
| GEO-SA | South America | 16 | M49 South America subregion. | POPULATED | NOT_RESEARCHED |
| GEO-OC | Oceania | 29 | M49 region 009. | POPULATED | NOT_RESEARCHED |
| GEO-AN | Antarctica | 1 | Geographic reference only; not an identity-document issuer jurisdiction. | POPULATED | NOT_APPLICABLE |
| **TOTAL** | **World inventory** | **248** | M49 country-or-area records. | **POPULATED** | **PENDING** |

## Country and area lists

- [Complete readable list by continent](COUNTRIES-AND-AREAS-BY-CONTINENT.md)
- [Structured country and jurisdiction CSV register](COUNTRY-AND-JURISDICTION-REGISTER.csv)

## Classification notes

The seven-continent navigation model does not map one-to-one to M49 macro-geographical regions. M49 groups North America, Central America, the Caribbean, and South America under the Americas region with separate subregions. For this project's navigation, Central America and the Caribbean are grouped under North America while the original M49 codes and names remain stored in the register.

M49 is a statistical geographic classification. It is not a legal determination of sovereignty, borders, citizenship, or the competence of an issuing institution. The register must preserve the distinction between sovereign states, territories, dependencies, and other areas wherever relevant.

## Next step

The geographic enumeration baseline is now populated. Institutional research has begun in 12 African jurisdictions. The next phase is to continue by jurisdiction, map each functional authority and subnational unit, and maintain explicit coverage statuses before any API or connector design. Do not mark an issuer as confirmed until its mandate is supported by official sources.
