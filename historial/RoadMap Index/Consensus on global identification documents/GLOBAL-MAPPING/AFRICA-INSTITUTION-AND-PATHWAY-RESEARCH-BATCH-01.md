# Africa — Institution and Lawful Pathway Research, Batch 01

## Scope and status

This first expansion adds civil registration, nationality/citizenship and protection institutions to the existing identity-document and passport issuer inventory.

- Geographic baseline: 60 M49 country-or-area records for Africa.
- Jurisdictions in this initial institutional pass: 11.
- Institution/role records created: 33.
- Research date: 2026-11-06.
- Master data file: [INSTITUTION-AND-PATHWAY-REGISTER.csv](INSTITUTION-AND-PATHWAY-REGISTER.csv).
- Research template: [INSTITUTION-AND-PATHWAY-RESEARCH-TEMPLATE.md](INSTITUTION-AND-PATHWAY-RESEARCH-TEMPLATE.md).
- Existing ID/passport records remain in [ISSUER-AND-API-REGISTER.csv](ISSUER-AND-API-REGISTER.csv).

The 11 jurisdictions are South Africa, Ghana, Nigeria, Kenya, Uganda, Rwanda, Ethiopia, Botswana, Zambia, Namibia and the United Republic of Tanzania. This is a first expansion batch, not complete African coverage and not a global institutional database.

## Key institutional findings

| Jurisdiction | Civil registration | Nationality / immigration | Protection / asylum |
|---|---|---|---|
| South Africa | Department of Home Affairs (DHA) manages civil records | DHA citizenship services | DHA manages refugee protection; statutory bodies have specific oversight/appeal roles |
| Ghana | Births and Deaths Registry | Ministry of the Interior naturalisation process; NIA is a separate identity registrar | Ghana Refugee Board receives and decides refugee-status applications |
| Nigeria | National Population Commission registers births/deaths | Ministry of Interior Citizenship and Business Department publishes naturalisation/registration requirements; NIMC and NIS remain separate identity/passport authorities | NCFRMI identified in statute and UNHCR guidance; exact operational allocation and decision chain still need primary government confirmation |
| Kenya | Civil Registration Services registers births/deaths irrespective of nationality | Directorate of Immigration Services handles passports and citizenship for qualifying foreigners; NRB handles national identity cards | Department of Refugee Services registers asylum/refugee claims and determines refugee status under the Refugees Act process |
| Uganda | NIRA registers births/deaths and manages the national identity register | NCIC administers citizenship and passports and acts as Secretariat to the National Citizenship and Immigration Board | OPM Department of Refugees is the secretariat to the Refugee Eligibility Committee and Refugee Appeals Board; distinguish the committee's decision-making role |
| Rwanda | NIDA integrates civil registration and the population registry; NCI-CRVS operates through decentralized registration offices | DGIE/public immigration system and 2021 Organic Law on Rwandan Nationality identified; detailed decision responsibility remains to be checked | 2024 Refugee Law identifies a competent decision-making organ; its exact institutional designation needs further legal confirmation |
| Ethiopia | Vital Events Registration Agency (VERA) appears in UNICEF's country CRVS profile; primary government confirmation still required. Addis Ababa has a separate city civil-registration agency | Immigration and Citizenship Service (ICS) operates passport and immigration service portal | Refugees and Returnees Service registers asylum seekers, performs refugee status determination and issues refugee documents |
| Botswana | Department of Civil and National Registration handles civil/vital statistics and Omang | Department of Immigration and Citizenship issues passports and administers citizenship/immigration services | Refugee status authority not identified in this pass; remains an explicit research gap |
| Zambia | DNRPC combines civil and national registration | DNRPC handles passport and citizenship functions | Office of the Commissioner for Refugees receives/processes recognition applications and coordinates refugee protection |
| Namibia | MHAISS Department of Civil Registration manages National Population Register and civil records | Department of Immigration Control and Citizenship handles passports and citizenship | MHAISS Department of Administration and Refugee Management supports/protects refugees and asylum seekers; exact adjudicator and appeals chain needs legal confirmation |
| Tanzania | RITA provides birth/death registration and certificate verification | Immigration Services Department handles passports and citizenship/nationality divisions | Refugee Services Department coordinates refugee matters and reviews asylum applications through the National Eligibility Committee; current procedure requires legal refresh |

## Significant design observations

### 1. One institution can carry multiple legal roles
South Africa's DHA and Zambia's DNRPC cover multiple areas. The data model therefore records mandate categories and authority levels separately. Where the same institution performs civil registration and citizenship processing, the database must still distinguish the legal effect of each service.

### 2. Birth registration is not nationality adjudication
The new register records civil registration as evidence of a vital event. It does not treat a birth certificate or place of birth as automatic proof of citizenship. For example, Kenya's Civil Registration Services states that birth/death registration applies irrespective of nationality; Ghana's BDR procedure asks for evidence when a parent's nationality is entered.

### 3. Protection authority is not nationality authority
Refugee status determination, refugee documentation and protection services are separate from nationality determination. The Ghana Refugee Board, Kenya DRS and Ethiopia RRS publish refugee-status functions; these cannot be substituted for citizenship decisions.

### 4. Decision-maker and secretariat must be represented separately
Uganda's OPM Department of Refugees serves as secretariat to the Refugee Eligibility Committee and the Refugee Appeals Board. It must not be conflated with the statutory decision-making bodies.

### 5. APIs are not assumed
This batch mainly records official portals, service pages and institutional processes. No new public third-party APIs or Node Core OS production connectors are asserted. Zambia's DNRPC e-services portal explicitly states that its civil/national registration features are under development. Tanzania's RITA certificate-verification form is not proof of a public API.

## Open research items

- Complete issuer, civil-registration, nationality, protection and statelessness coverage for the remaining 49 African M49 records.
- Obtain primary government confirmation of Ethiopia's nationwide VERA mandate and current organizational structure.
- Confirm the legal/administrative decision authority for nationality cases in Ghana, Nigeria, Rwanda, Namibia and Tanzania.
- Identify Nigeria's current refugee-status adjudication chain and confirm NCFRMI's exact operational remit under the 2022 Act.
- Confirm Rwanda's designated organ for refugee-status decisions under Law No. 042/2024.
- Identify Botswana's current refugee-status determination authority and any statelessness procedures.
- Confirm Namibia's current asylum adjudication and appeal bodies.
- Research dedicated statelessness determination or protection pathways in all 11 jurisdictions; no such procedure is asserted merely because a refugee or migration body exists.
- Locate official API documentation and access conditions for every institution; no API should be inferred from an online application portal.

## Sources

The master CSV stores the evidence URL and source type per institution. Key primary source examples include:

- South Africa DHA: https://www.gov.za/about-government/government-system/home-affairs
- Ghana BDR: https://bdr.gov.gh/about/
- Ghana Ministry of the Interior: https://www.mint.gov.gh/public/services/naturalization-as-ghanaian-citizen
- Ghana Refugee Board: https://grb.gov.gh/Function
- Nigeria National Population Commission: https://www.nationalpopulation.gov.ng/about
- Kenya Civil Registration Services: https://crs.ecitizen.go.ke/
- Kenya Department of Refugee Services: https://refugee.go.ke/refugee-status-determination-rsd
- Uganda NIRA: https://nira.go.ug/
- Uganda NCIC: https://www.immigration.go.ug/institutional-mandate
- Uganda OPM Department of Refugees: https://opm.go.ug/refugees/
- Rwanda NIDA: https://www.nida.gov.rw/about-nida
- Ethiopia RRS: https://rrs.et/registration-and-protection/
- Botswana government ministry: https://gov.bw/ministries/ministry-labour-and-home-affairs
- Zambia DNRPC: https://www.mohais.gov.zm/?page_id=1115
- Zambia Office of the Commissioner for Refugees: https://www.mohais.gov.zm/?page_id=1567
- Namibia Civil Registration: https://mha.gov.na/civil-registration
- Tanzania RITA: https://erita.rita.go.tz/
- Tanzania Immigration Services Department: https://www.immigration.go.tz/

