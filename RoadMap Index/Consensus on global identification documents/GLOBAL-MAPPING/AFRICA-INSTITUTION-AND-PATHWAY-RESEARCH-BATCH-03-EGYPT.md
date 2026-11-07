# Africa — Institution and Lawful Pathway Research, Batch 03: Egypt

## Scope and status

This batch adds Egypt (M49 818; ISO EG) as the thirteenth African jurisdiction with initial institution and pathway mapping.

- African geographic baseline: 60 M49 country-or-area records.
- Jurisdictions with institutional research started: 13.
- Institution records added for Egypt: 5.
- Issuer/document records added for Egypt: 3.
- Lawful-procedure records added for Egypt: 2.
- Research date: 2026-11-06.
- Master files: [Institution and Lawful Pathway Register](INSTITUTION-AND-PATHWAY-REGISTER.csv), [Issuer and API Register](ISSUER-AND-API-REGISTER.csv), [Lawful Identity Pathway Register](LAWFUL-IDENTITY-PATHWAY-REGISTER.csv).
- Coverage matrix: [Mapping Coverage Register](MAPPING-COVERAGE-REGISTER.csv).
- Parent/child relationships: [Institution Relationship Register](INSTITUTION-RELATIONSHIP-REGISTER.csv).

The map is intentionally partial. The current pass does not yet complete the local civil-registration office structure, every nationality route, the statelessness determination framework, or the full subnational service network.

## Egypt — initial institutional map

| Layer | Institution | Function mapped | Evidence status |
|---|---|---|---|
| Civil registration and national identity | Civil Status Sector, Ministry of Interior | Civil-status records and national ID card services | Initial official-source confirmation; local hierarchy remains open |
| Passports and nationality | Passports, Emigration and Nationality Administration (PENA), Ministry of Interior | Passport, nationality, migration and residence services | Official PENA portal |
| Consular intake | Ministry of Foreign Affairs, Emigration and Egyptian Expatriates | Consular passport, birth-record, national-ID and nationality-related applications; forwards matters to competent authorities | Official MFA service directory |
| Statutory asylum authority | Permanent Committee for Refugee Affairs | Law No. 164/2024 assigns national asylum functions to the Committee | Legal authority established; operational transition not yet confirmed |
| Current protection operation | UNHCR Egypt Operation | Registration, asylum documentation and refugee status determination under the existing cooperation arrangement | UNHCR says it continues until the national system is fully operational |

## Critical transition: national asylum system

Egypt enacted Asylum Law No. 164 of 2024, establishing a Permanent Committee for Refugee Affairs under the Prime Minister's authority. The executive regulations were published in May 2026. However, the legal creation of the Committee and publication of regulations must not be confused with a fully operational transfer of casework.

UNHCR's current Egypt country page states that, under the 1954 Memorandum of Understanding, UNHCR continues registration, asylum documentation, refugee status determination, resettlement, voluntary repatriation and related protection functions until the national asylum system is fully operational. The mapping therefore records both the statutory Committee and the current UNHCR operational role, with an explicit transition warning.

**Routing rule:** do not send an applicant to a presumed fully operational Committee based solely on the law or regulations. Confirm the official start date, operational channels and transfer of caseload with the Egyptian authorities and UNHCR before providing a live referral.

## Nationality and document pathways

The PENA official portal publishes distinct nationality routes, including applications related to acquisition, restoration and proof of Egyptian nationality. The Ministry of Foreign Affairs publishes consular procedures and notes that some applications are reviewed by the consulate and forwarded to the competent PENA administration.

The Ministry's consular service directory also documents national ID renewal and birth-certificate services for Egyptian citizens abroad. These are administrative and consular service pathways; they are not a universal entitlement to Egyptian nationality and do not establish that a person without documents qualifies for citizenship.

The current map distinguishes:
- Civil-status and birth records.
- National ID card issuance/renewal.
- Ordinary passport issuance.
- Nationality applications and proof-of-nationality services.
- Refugee registration and status documentation under the current transition arrangement.

No statelessness determination procedure has been confirmed in this batch. That category remains **NOT_RESEARCHED**, not “not available.”

## API and connector boundary

This batch records official administrative services and legal/operational responsibilities only. It does not claim that any government or UNHCR API is public, that Node Core OS has a connection, or that third-party access to case records is permitted. Digital or consular portals are not automatically APIs. API and connector work remains deferred until institutional mapping is sufficiently complete.

## Sources

- [Egypt PENA official portal]( https://www.moi.gov.eg/Passportsen_fr/home/Index )
- [PENA nationality services]( https://moi.gov.eg/passportsen_fr/nationality/index/7 )
- [Egypt Ministry of Foreign Affairs — Consular Services]( https://www.mfa.gov.eg/js/ConsularServicesAndTransactions )
- [UNHCR Egypt country operation and transition update]( https://www.unhcr.org/where-we-work/countries/egypt )
- [Egypt Asylum Law No. 164 of 2024 — Refworld legal text]( https://www.refworld.org/legal/legislation/natlegbod/2024/149388?lang=ar )
- [Executive Regulations of the Asylum Law — legal analysis, 1 July 2026]( https://ww.eipr.org/en/publications/executive-regulations-asylum-law )

## Open research items

1. Confirm the full national and governorate-level structure of the Civil Status Sector and local birth/marriage/death registration offices.
2. Map the nationality routes under Law No. 26 of 1975 and subsequent amendments, including decision-maker and judicial review for each route.
3. Confirm the current effective date and operational status of the Permanent Committee for Refugee Affairs, including the technical secretariat and actual transfer of UNHCR caseload.
4. Map the statutory refugee documentation and travel-document procedures under the 2026 executive regulations.
5. Research any Egyptian statelessness determination or protection procedure and identify the competent authority, if one exists.
6. Map the regional and local PENA branches, Civil Status offices and relevant consular channels.
7. Confirm whether official verification services exist and classify access conditions only after primary-source research; do not infer APIs.
