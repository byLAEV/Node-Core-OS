# Issuer Mapping Scope and Coverage Rules

## 1. Primary objective

Build a worldwide directory that identifies, for every applicable country, area or special jurisdiction:

1. The authority that issues the relevant national or resident identity document.
2. The authority that issues the passport or state travel document.
3. The official website or direct official service page for each authority.

The completion target is an attributable issuer name and an official web source, not an API. If the responsible authority cannot yet be confirmed, the record remains visibly pending. A blank field must never be interpreted as proof that the issuing function does not exist.

## 2. Geographic scope

The country/area baseline is the 248-record UN M49 dataset already stored in `COUNTRY-AND-JURISDICTION-REGISTER.csv`. It includes 247 country/area jurisdictions and Antarctica as a geographic reference only.

The project presents the baseline through seven continental navigation groups:
- Africa
- Asia
- Europe
- North America, including Central America and the Caribbean
- South America
- Oceania
- Antarctica, geographic reference only

M49 is used as a stable statistical index. It does not determine sovereignty, legal status, or the issuing authority of a territory.

## 3. Special and out-of-continent authorities

The mapping must not be limited to sovereign countries or to one issuer per continent.

### 3.1 Special jurisdictions within the geographic baseline

Where an autonomous, dependent, overseas or special administrative area has a distinct identity-card or passport issuer, record it as its own linked jurisdictional row. Preserve its M49/ISO identifiers and its constitutional or administrative relationship to the parent State.

Examples already identified in the Asian part of the baseline include the Hong Kong SAR Immigration Department and the Macao SAR Identification Services Bureau. Their local identity documents and SAR passports are recorded separately from the general PRC issuer structure.

### 3.2 Global, regional and non-territorial organizations

Some organizations issue restricted official travel documents to their staff, officials or diplomatic representatives. They do not necessarily issue ordinary national passports or public identity cards.

Keep them in `EXTRACONTINENTAL-AND-REGIONAL-DOCUMENT-ISSUERS.csv`, outside the 247-jurisdiction coverage denominator. Initial examples include:
- Sovereign Military Order of Malta — diplomatic and service passports for limited eligible holders.
- European Union — EU laissez-passer for eligible institutional representatives and staff.
- United Nations — UN laissez-passer for eligible UN officials.

Classify each document accurately. Do not count a laissez-passer or restricted service document as a national passport, citizenship document or general identity card.

## 4. Minimum data requirements

For each jurisdiction row:
- Stable geographic and jurisdiction ID.
- Continent navigation group and M49 region/subregion.
- Official country/area name, M49 code and ISO code where available.
- Identity-document category and issuing-authority name.
- Identity issuer official website or direct government service page.
- Passport/travel-document category and issuing-authority name.
- Passport issuer official website or direct government service page.
- Separate status for identity issuer and passport issuer.
- Source URLs and review date.
- Notes describing special jurisdiction status or unresolved authority questions.

One institution may issue both documents; in that case it must still be linked to both document categories. Different branches of one ministry should not be collapsed if the legally responsible issuer differs.

## 5. Document classification

Keep these document families distinct:
- National or resident identity card.
- Ordinary national passport.
- Diplomatic, official or service passport.
- Stateless-person or refugee identity document.
- Refugee or stateless-person travel document.
- Restricted international-organization laissez-passer or institutional travel document.

A resident identity card does not necessarily prove citizenship. A refugee identity document does not become a national identity card. A travel document is not automatically a passport. A civil-registration authority does not automatically issue identity cards or passports.

## 6. Coverage status values

- `AUTHORITY_IDENTIFIED`: an official authority is named and supported by a primary source.
- `RESEARCH_IN_PROGRESS`: research has started but the required authority/source combination is incomplete.
- `NOT_RESEARCHED`: issuer research has not yet been performed or recorded.
- `NOT_APPLICABLE`: the row is not an issuer jurisdiction or the particular issuer category does not apply, supported by evidence.
- `SOURCE_REVIEW_REQUIRED`: evidence is incomplete, conflicting or due for revalidation.

Do not use `NOT_APPLICABLE` merely because an issuer was not found. Unknowns must remain unknown.

## 7. Completion criteria

The core issuer-mapping phase is complete when:
1. Every applicable M49 country/area record has an identity issuer status and a passport issuer status.
2. Every identified authority has an official name and an official web source.
3. Every special jurisdiction with distinct issuing powers is represented separately and linked to its parent jurisdiction.
4. Global, regional and non-territorial issuing organizations are represented in the separate register when they issue relevant documents.
5. Each record differentiates a confirmed issuer from an applicant portal, civil registry, service operator or unrelated institution.
6. The register can be validated for unique IDs, valid geographic references, source links and status consistency.

No API, integration, document verification API or institutional permission is required to complete this phase.

## 8. Deferred phases

After the issuer map is sufficiently complete, Node Core OS may separately map legal mandates, application procedures, eligibility, travel/visa requirements, identity verification mechanisms, APIs and authorized connectors. Those activities must not be allowed to redefine or delay the minimum issuer-directory objective.
