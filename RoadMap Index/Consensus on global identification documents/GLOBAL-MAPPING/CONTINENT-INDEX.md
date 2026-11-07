# Continental and Geographic Region Index

This index is the top-level navigation layer for the global issuer map.

## Geographic organization

The project will use a seven-continent navigation model while storing standardized region and subregion identifiers from the United Nations Statistics Division M49 classification where applicable.

Reference: https://unstats.un.org/unsd/methodology/m49/

| Navigation ID | Continent / geographic scope | Mapping notes | Status |
|---|---|---|---|
| GEO-AF | Africa | Countries and areas will be indexed by M49 region/subregion. | NOT_RESEARCHED |
| GEO-AS | Asia | Countries and areas will be indexed by M49 region/subregion. | NOT_RESEARCHED |
| GEO-EU | Europe | Countries and areas will be indexed by M49 region/subregion. | NOT_RESEARCHED |
| GEO-NA | North America | M49 Americas subregions will be retained as source metadata. | NOT_RESEARCHED |
| GEO-SA | South America | M49 Americas subregions will be retained as source metadata. | NOT_RESEARCHED |
| GEO-OC | Oceania | Countries and areas will be indexed by M49 region/subregion. | NOT_RESEARCHED |
| GEO-AN | Antarctica | Geographic reference only; do not assume a national identity-document issuer. | NOT_APPLICABLE_PENDING_REVIEW |

## Important classification note

The seven-continent navigation model does not map one-to-one to M49 macro-geographical regions. For example, M49 groups North America, Central America, the Caribbean, and South America under the Americas region with separate subregions. Preserve both the project's navigation ID and the official M49 identifiers so the dataset remains searchable and consistent.

## Next step

Populate the country and area register from an authoritative geographic dataset, then research issuing authorities jurisdiction by jurisdiction. Do not mark a continent as mapped until its countries/areas and their research statuses have been enumerated.
