# Global Functional Domain Map — Node Core OS byLAEV

**Status:** Mapping framework and research specification  
**Scope:** Worldwide, across all mapped countries, territories and jurisdictions  
**Principle:** One shared geographic and institutional knowledge base; multiple functional applications.

## 1. Purpose

Node Core OS byLAEV is mapping the world's functional institutional infrastructure so its nodes can transform fragmented public information into useful, source-backed services. This is broader than a list of countries or identity issuers. It is a structured representation of where rules are made, who has legal authority, which offices operate procedures, what services exist and how people can lawfully access them.

The map supports people regardless of where they are located. It must also handle people whose identity or nationality is uncertain without assuming that a missing document means that a person is stateless.

## 2. Functional domains

| Domain | What the map must discover | Example node capability |
|---|---|---|
| Identity and civil status | Civil registries, birth registration, late registration, record retrieval/correction, identity issuers, archives, evidence and appeals | Build a documented route to recover or establish civil identity |
| Nationality and citizenship | Nationality laws, descent/birth rules, acquisition, naturalization, competent authorities, courts, consulates, statelessness safeguards | Identify possible legal nationality pathways and the authority that decides |
| International travel | Visa, transit, entry, passport validity, travel-document recognition, permitted stay, border rules and consular notices | Check destination requirements using the traveler's actual circumstances |
| Residence and migration | Entry visas, residence permits, work/study routes, family reunification, renewals, permanent residence, regularization and appeals | Find lawful routes to enter, reside or change status |
| Education | Admissions, public education access, accreditation, qualification recognition, equivalency, student permits and scholarships | Identify study options and document/qualification requirements |
| Work and professions | Work authorization, labor registration, occupational licensing, regulated professions, qualification recognition and social security | Identify lawful work routes and professional recognition requirements |
| Public and essential services | Relevant public-service authorities, eligibility, application channels, evidence and complaint/review routes | Locate the competent public service and understand access conditions |
| Institutional/digital services | Official portals, documented APIs, authentication, access agreements, consent, data-protection terms and technical limitations | Use an authorized digital service where an integration is actually available |

These domains share a common map. Each application should consume the same jurisdiction and institution records rather than maintain a separate country database.

## 3. Macro-to-micro hierarchy

1. **World and multilateral layer:** global treaties, international standards, UN agencies and other multilateral bodies.
2. **Continental and regional layer:** regional organizations, conventions, mobility frameworks and regional courts or commissions.
3. **Country, territory and jurisdiction layer:** constitutional order, territorial scope, applicable legislation and jurisdictional distinctions.
4. **Institution layer:** ministries, civil registries, courts, immigration authorities, consulates, education authorities, labor authorities and other competent bodies.
5. **Operational unit layer:** directorates, departments, local offices, registrars, consular posts, service desks and archives.
6. **Procedure and service layer:** eligibility, evidence, forms, deadlines, fees, decisions, review and appeal.
7. **Digital access layer:** official portals, documented APIs, partner onboarding, access controls and integration requirements. This layer is researched after the preceding layers are mapped.

The map must distinguish legal authority, decision-maker, service operator, referral body and source of information. These roles are not interchangeable.

## 4. Context required for a correct answer

A node must not return a universal answer when the applicable rule depends on personal or situational variables. Relevant context may include:

- Nationality or possible nationalities, including unresolved status.
- Type, issuer, validity and condition of travel document.
- Current location and legal residence.
- Destination, transit countries and travel dates.
- Purpose and duration of travel or stay.
- Age and relevant family relationships.
- Birthplace, parentage and dates relevant to nationality law.
- Education level, qualification, institution and accreditation.
- Occupation, licensing status and regulated-profession classification.

Collect only the minimum information needed for the requested service. Sensitive personal documents and case files must not be placed in public repositories, public IPFS, or public blockchains.

## 5. Record requirements

A domain-specific record should contain, where applicable:

- Stable record ID and jurisdiction identifier.
- Functional domain and service/procedure category.
- Competent institution and actual decision-maker, if different.
- Operational office and territorial scope.
- Legal basis and official procedure source.
- Eligibility and excluded categories.
- Required evidence and accepted alternatives.
- Application channel (in person, postal, online, consular).
- Fees, processing times and deadlines, only when officially supported.
- Appeal, review, complaint and referral route.
- Effective date, last-checked date and source status.
- Evidence confidence, outstanding questions and change history.

Use explicit states such as NOT_RESEARCHED, SOURCE_REVIEW_REQUIRED, PARTIALLY_MAPPED, PRIMARY_SOURCE_CONFIRMED, MAPPED, NOT_APPLICABLE and NOT_PUBLICLY_DOCUMENTED. Do not treat missing data as proof that a service or legal route does not exist.

## 6. International travel and migration: special rules

Travel and migration requirements change frequently and may depend on nationality, travel document, residence, route, purpose and date. A future application must cite the relevant official immigration, foreign-affairs, border or consular source and show the date checked. Commercial travel sites may help discover leads but cannot replace the competent authority's rule.

The map must distinguish:
- Visa exemption from permission to enter.
- Visa issuance from admission at the border.
- Transit permission from destination entry permission.
- Passport validity rules from visa validity.
- Residence permission from work authorization.
- Refugee travel documents and other non-national passports from ordinary national passports.

Do not promise entry, a visa, residence, employment or legal status. Final decisions belong to the competent State authority.

## 7. Identity, nationality and protection safeguards

A person without identity documents is not automatically stateless. The map should preserve the difference between lack of documents, undetermined nationality, a claim to nationality, and formally recognized statelessness. A Node Core OS credential can preserve a person's network identity and evidence history, but it is not a State-issued identity document, passport or nationality decision.

The system can help identify possible legal routes, prepare evidence inventories, find official procedures and refer users to competent authorities or qualified legal assistance. It cannot grant citizenship or replace legal adjudication.

## 8. API and connector policy

An official website, online form, public search page or applicant portal does not establish the existence of an API. For each interface, record the technical documentation, owner, allowed purpose, eligibility, authentication, authorization, consent requirements, contract/onboarding, rate limits, data retention and security obligations.

No API connector should be implemented merely because an institution appears in the map. API assessment follows the mapping of the relevant institution, service and lawful access route.

## 9. Completion criteria

The worldwide map is not complete when every country has a name. Completion requires:
- Geographic and jurisdictional coverage.
- Institutional hierarchy and competence mapping.
- Relevant procedures across the functional domains.
- Official sources, effective dates and review status.
- Decision-makers, operational offices and review routes.
- Explicit unknowns and documented non-applicability.
- Cross-border and regional relationships where relevant.
- Repeatable validation of record identifiers, references and completeness.

Coverage must be reported by domain and jurisdiction. A country may be mapped for civil identity but remain unmapped for education, employment or travel. No single MAPPED label should hide these differences.

## 10. Research sequence

1. Maintain the global geographic baseline.
2. Complete the macro-to-micro institutional hierarchy.
3. Continue detailed identity and nationality research already underway.
4. Expand country-by-country research into travel, migration, education and work.
5. Add relevant public-service and regional/multilateral layers.
6. Verify sources, effective dates, decision-makers and appeal routes.
7. Validate data structure and coverage.
8. Assess APIs and connectors only for mapped services with documented lawful access.

**The objective:** turn dispersed worldwide institutional knowledge into a dependable shared foundation from which Node Core OS applications can provide practical, contextual and verifiable services to their nodes.
