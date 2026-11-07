# Africa — Institution and Lawful Pathway Research, Batch 02

## Scope and status

This batch adds Senegal as the twelfth African jurisdiction with source-backed institutional and legal-pathway records.

- Geographic baseline: 60 M49 country-or-area records in Africa.
- Prior institutional pass: 11 African jurisdictions.
- This batch: Senegal (M49 686; ISO SN).
- New institution records: 6.
- New issuer/document records: 4.
- New lawful-procedure records: 4.
- Research date: 2026-11-06.
- Master files: [INSTITUTION-AND-PATHWAY-REGISTER.csv](INSTITUTION-AND-PATHWAY-REGISTER.csv), [ISSUER-AND-API-REGISTER.csv](ISSUER-AND-API-REGISTER.csv), [LAWFUL-IDENTITY-PATHWAY-REGISTER.csv](LAWFUL-IDENTITY-PATHWAY-REGISTER.csv).
- Coverage matrix: [MAPPING-COVERAGE-REGISTER.csv](MAPPING-COVERAGE-REGISTER.csv).
- Parent/child links: [INSTITUTION-RELATIONSHIP-REGISTER.csv](INSTITUTION-RELATIONSHIP-REGISTER.csv).

This is partial jurisdictional coverage. Civil registration offices, nationality certificates and adjudication, subnational office lists, and detailed immigration/residence appeal bodies remain open research items.

## Senegal — institutional map

| Institutional layer | Identified authority / unit | Mapped function | Status |
|---|---|---|---|
| Final legal decision | Presidency / President of the Republic | Refugee or stateless status is formally granted by decree after the statutory process | Primary legal text confirmed |
| National status institution | Commission nationale de Gestion des Réfugiés et des Apatrides (CNGRA) | Receives applications, registers cases, interviews applicants, routes files to eligibility and recourse committees, prepares draft decrees | Primary legal text confirmed |
| Legal document issuer | Ministry of the Interior and Public Security | Issues biometric identity and travel documents for persons admitted as refugees or stateless persons | Decree No. 2025-1560 |
| Population files and ID operations | Direction de l'Automatisation des Fichiers (DAF) | Manages non-police population files and national ID production; published remit lists foreigner and refugee identity-card files | Primary ministry page; exact production role for stateless cards remains open |
| Police / passport hierarchy | Direction générale de la Police nationale (DGPN) → Direction de la Police des Étrangers et des Titres de Voyage (DPETV) | Passport, travel-document and foreigner-administration service routes | Ministry organizational/service pages |

## Critical legal pathway: statelessness recognition

Senegal's Law No. 2022-01 of 14 April 2022 established a national legal framework for refugees and stateless persons and created the CNGRA. Decree No. 2025-1559 of 17 September 2025 sets the admission requirements and procedure for both statuses.

The decree states that a person may be admitted as stateless where no State considers that person a national under the operation of its law. This is a formal legal status; it is not equivalent to merely lacking an identity card, passport, birth certificate, or other evidence.

The mapped process is:

1. The applicant submits the request to the CNGRA Permanent Secretariat or territorially competent regional committee. The decree permits electronic filing.
2. The CNGRA registers the file, issues a receipt, opens an individual case record, arranges an interview and coordinates the investigation.
3. The Eligibility Committee examines the case and issues a reasoned opinion.
4. An unfavourable eligibility opinion can be appealed to the CNGRA Committee of Recourse within 45 days. A negative decision of the Committee of Recourse may be challenged before the Supreme Court for excess of power.
5. Following a favourable opinion, the CNGRA prepares the draft admission decree. The refugee or stateless status is granted by decree; the network or the CNGRA record alone is not the status decision.

## State-issued documents after recognition

Decree No. 2025-1560 of 17 September 2025 sets the form, duration and issuance procedure for biometric identity cards and travel documents for refugees and stateless persons:

- The Ministry of the Interior and Public Security is the issuing ministry.
- The application for the biometric identity card is routed through the CNGRA and requires the admission decree, a birth extract or a CNGRA certificate in lieu, and other evidence needed to verify identity and status.
- The biometric card is valid for five years.
- A travel document requires the relevant identity card, a justified travel purpose, a birth record or equivalent, a UNHCR ProGres attestation and the applicable fiscal stamp.
- The biometric travel document is valid for five years, with defined renewal/extension arrangements.
- The CNGRA coordinates and supervises issuance and renewal with the Ministry.

These are refugee/stateless identity and travel documents. They are not Senegalese nationality, a Senegalese national identity card for citizens, or an ordinary Senegalese passport.

## National ID and ordinary passport routes

The Ministry's biometric national identity-card page says the national card is available to Senegalese citizens from age five. It identifies DAF as the service contact and says that a person whose nationality is in doubt must provide a certificate of nationality.

The ordinary passport page states that Senegalese citizens may apply from birth. It points applicants to police stations and the DPETV for more information, and to Senegalese embassies for applicants abroad. The Ministry's passport route is distinct from the refugee/stateless travel-document route.

## API and integration boundary

This batch maps institutions and legal procedures only. It does not assert that an API is available, that Node Core OS is connected to the CNGRA or the Ministry, or that third-party access to case records is permitted. The Decree's permission for electronic filing is not proof of a public API. API discovery remains deferred until the institutional map is sufficiently complete.

## Sources

- Senegal Ministry of the Interior — DAF mandate: https://interieur.gouv.sn/le-ministere/directions/direction-de-l-automatisation-des-fichiers-daf
- Senegal Ministry — biometric national identity card: https://interieur.gouv.sn/services/services-aux-usagers/carte-nationale-d-identite-biometrique
- Senegal Ministry — ordinary passport: https://interieur.gouv.sn/services/services-aux-usagers/passeport-ordinaire
- Senegal Ministry — foreigner identity card: https://interieur.gouv.sn/services/services-aux-usagers/carte-d-identite-d-etranger
- Senegal Ministry — DGPN organizational page: https://interieur.gouv.sn/le-ministere/directions-generales/direction-generale-de-la-police-nationale-dgpn
- Decree No. 2025-1559 (published presidential decree text copy): https://www.refworld.org/sites/default/files/2025-12/decret_2025-1559-statut_refugies_et_apatrides_senegal.pdf
- Official Journal No. 7861, 8 November 2025 (index listing Decrees No. 2025-1559 and No. 2025-1560): https://www.archives.sn/docs/journal-officiel/jo-7861-08-novembre-2025
- Decree No. 2025-1560, legal text: https://legi.sn/legislation/7861_1777919665992_zg4kkm

## Open research items

- Identify and map civil-status registrar offices and the current national supervisory authority for birth, marriage and death registration.
- Confirm the route, competent courts and appeal mechanisms for Senegalese nationality certificates and nationality disputes.
- Confirm the operational regional committee names, locations and contact points for the CNGRA.
- Confirm current implementation of the CNGRA electronic filing channel and whether any machine interface is documented; do not assume an API.
- Confirm which Ministry unit physically produces the new biometric identity and travel documents for recognized stateless persons.
- Map legal-aid and civil-society organizations that provide authorized support or referrals.
- Complete the remaining 48 African M49 country-or-area records, then continue institutional mapping across Asia, Europe, the Americas and Oceania.
