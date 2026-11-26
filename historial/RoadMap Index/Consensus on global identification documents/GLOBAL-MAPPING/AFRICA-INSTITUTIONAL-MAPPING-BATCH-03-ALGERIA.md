# Africa — Institutional Mapping Research Batch: Algeria

**Jurisdiction:** Algeria (UN M49 012; ISO DZ)  
**Research date:** 2026-11-06  
**Coverage status:** PARTIALLY_MAPPED — this is not a complete jurisdictional map.

## 1. Institutional structure identified

| Layer | Institution | Confirmed role | Open questions |
|---|---|---|---|
| Civil status and identity | Ministry of Interior, Local Authorities and Transport | Official portal lists birth, marriage and death certificates, biometric national identity card applications and secure-document tracking | Exact municipal registrar chain, late registration, correction and appeal procedures |
| Nationality and justice | Ministry of Justice and court network | Nationality certificates are available through courts, consular representations and an online service after identity verification; publishes nationality-acquisition document requirements | Route-specific decision-maker, evidentiary rules and review mechanisms |
| Civil status abroad | Ministry of Foreign Affairs and diplomatic/consular posts | Transcribes foreign birth/marriage records and provides copies of records held by consular posts | Individual post jurisdictions, record retention, correction and judicial referral |
| Refugee/statelessness framework | BAPRA, established under Decree No. 63-274 of 25 July 1963 | Statutory bureau within the Ministry of Foreign Affairs for refugee and stateless-person protection | Current operational activity, individual statelessness determination, intake and state-issued documents |
| Refugee registration and RSD | UNHCR Algeria | Continues registration and refugee status determination in absence of a national asylum law | Future transition to State-led system; keep operational status under review |

## 2. Civil registration and biometric identity

The Ministry's official citizen-services portal lists civil-status services for birth, marriage and death certificates, applications for the electronic/biometric national identity card, and secure-document application tracking. This confirms the public-facing service categories, but not an external API.

Official portal: https://services.interieur.gov.dz/en/request/

The Ministry of Foreign Affairs publishes a separate route for Algerian citizens born or married abroad. Its Civil Status Service can issue copies of records previously entered in diplomatic/consular registers and receive transcription requests, then forward files to the territorially competent diplomatic or consular post. The published birth-transcription evidence may include the applicant's foreign birth record and the civil-status records of the relevant parent and grandparent; requirements differ according to the nationality link and legal route.

Official procedure: https://mfa.gov.dz/services-for-algerians/civil-status-1

## 3. Nationality certificates and nationality acquisition

The Ministry of Justice states that an Algerian nationality certificate may be issued by any court in the national territory, a national diplomatic or consular representation abroad, or online through the Ministry's service. The online process described by the Ministry requires an initial identity-verification process at a court counter, after which credentials are provided for subsequent online requests.

Official procedure: https://www.mjustice.gov.dz/en/at-the-level-of-the-courts/

A Ministry notice dated 26 October 2025 states that, from 16 March 2025, citizens whose identity is already verified in the national database may obtain the certificate at the nearest court by presenting a biometric national identity card or biometric passport. Persons not yet verified must provide documents establishing their entitlement; their identity is then registered in the verified database.

Notice: https://www.mjustice.gov.dz/en/obtaining-the-algerian-certificate-of-nationality-by-presenting-the-biometric-national-identity-card-or-the-biometric-national-passport/

The Ministry also publishes a document list under Article 9 bis of Ordinance No. 70-86. This is a distinct acquisition-of-nationality pathway and must not be confused with a routine certificate proving an existing nationality.

Document list: https://www.mjustice.gov.dz/wp-content/uploads/2024/09/article_9_bis_en.pdf

## 4. Passport route

The Ministry's passport page states that applications may be filed at any commune in the same wilaya or at the relevant consular service for Algerians living abroad. For first-time applications, a nationality certificate may be required where the applicant has not previously received a national identity card issued on the basis of such a certificate.

Official procedure: https://interieur.gov.dz/passeport-national/

This establishes a public administrative procedure, not a public verification API or third-party access right.

## 5. Refugees and stateless persons

UNHCR's Algeria country profile states that Algeria has no national asylum law in force and that UNHCR continues to register asylum-seekers and conduct refugee status determination under its mandate. UNHCR's applicant-facing procedure describes email or in-person intake at its Algiers office, registration and interviews, asylum-seeker documentation, refugee status determination, and a written appeal within 30 days after a negative decision.

Sources:
- https://www.unhcr.org/where-we-work/countries/algeria
- https://help.unhcr.org/algeria/asylum-in-algeria/applying-for-asylum/
- https://help.unhcr.org/algeria/asylum-in-algeria/the-asylum-procedure-in-algeria/

UNHCR's Rights Mapping and Analysis Platform identifies BAPRA as established by Decree No. 63-274 of 25 July 1963 within the Ministry of Foreign Affairs to oversee legal and administrative protection of refugees and stateless persons. The available source does not establish the bureau's current case-intake operations or a current individual statelessness determination procedure. Those items remain explicitly open.

Source: https://rimap.unhcr.org/countries/algeria

UNHCR also publishes legal-assistance referrals for registered asylum-seekers and refugees, including support with civil documentation such as birth certificates. These services are confidential and assessed individually; the Node Core OS map must not expose or request private case files.

Source: https://help.unhcr.org/algeria/legal-assistance/

## 6. API and data-access boundary

This research records official service channels only. It does not establish:
- A public API for the civil-status or national identity databases.
- Third-party access to nationality verification systems.
- API access to passport or consular records.
- Access to UNHCR protection or case-management records.
- Permission to query BAPRA or individual refugee/statelessness files.

An official online portal or online certificate service is not, by itself, evidence of an API. API mapping and connector implementation remain deferred.

## 7. Remaining work for Algeria

- Map municipal civil-status offices and wilaya-level supervision.
- Identify the competent offices and courts for late birth registration, record correction and judicial transcription orders.
- Map nationality by descent, birth, marriage, adoption and naturalization against current legislation and amendments.
- Verify the legal decision-maker and review route for each nationality-acquisition pathway.
- Confirm BAPRA's present operational status, referral route, and any current state-led statelessness determination process.
- Map the consular jurisdictions and record-holding posts.
- Identify official archives and retention arrangements.
- Confirm the current status of asylum-law reform and any formal transfer of functions from UNHCR to Algerian authorities.
- Identify local legal-aid partners from current authoritative sources without exposing confidential case information.

## 8. Sources and research standard

Primary institutional sources were used for civil-status services, nationality certificates, nationality-acquisition documentation, consular transcription and passport procedures. UNHCR sources were used for refugee operations, the historical BAPRA mandate and legal-aid referral context. Where a current operational function could not be verified, the record is marked as pending rather than inferred.
