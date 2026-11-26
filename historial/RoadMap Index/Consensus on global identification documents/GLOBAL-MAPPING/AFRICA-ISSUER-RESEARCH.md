# Africa — Identity Document and Passport Issuer Research

## Research scope and status

This is the first institutional research batch for the African geographic group in the global mapping project.

- African M49 country-or-area records in the geographic register: **60**.
- Jurisdictions researched in this batch: **11**.
- Issuer records added to the master register: **22** (one national identity record and one passport record for each researched jurisdiction).
- Remaining African geographic records not yet researched for issuers: **49**.
- Research date: **2026-11-06**.

The 11 jurisdictions in this batch are South Africa, Ghana, Nigeria, Kenya, Uganda, Rwanda, Ethiopia, Botswana, Zambia, Namibia, and the United Republic of Tanzania. This is a first batch, not a complete African issuer directory.

The structured source of truth is [ISSUER-AND-API-REGISTER.csv](ISSUER-AND-API-REGISTER.csv). This report is a human-readable summary. Each issuer record must be revisited when official sources, laws, APIs, or access requirements change.

## Findings by jurisdiction

| Jurisdiction | National identity document authority | Passport authority | Institutional API / verification finding |
|---|---|---|---|
| South Africa | Department of Home Affairs (DHA) | Department of Home Affairs (DHA) | DHA announced a National Population Register identity-verification service for government and private-sector clients. It is an institutional service; public API documentation and onboarding specifications were not identified. |
| Ghana | National Identification Authority (NIA) — Ghana Card | Ministry of Foreign Affairs and Regional Integration — Ghana Passport Services | NIA offers real-time institutional identity verification. Access requires formal onboarding, supporting legal and data-protection documents, technical setup, and a service contract. Public API endpoints/specification were not identified. |
| Nigeria | National Identity Management Commission (NIMC) — NIN and national identity management | Nigeria Immigration Service (NIS) | NIMC advertises NIN verification/authentication services and NINAuth; external API documentation and access terms require confirmation. Passport application services are published by NIS; no external passport verification API was confirmed. |
| Kenya | National Registration Bureau (NRB) — national identity cards | Directorate of Immigration Services | Official passport application is through eCitizen, with biometric enrolment at passport processing centres. A third-party verification API was not confirmed for either issuer. |
| Uganda | National Identification and Registration Authority (NIRA) — National Identification Register / national ID | Directorate of Citizenship and Immigration Control / National Citizenship and Immigration Control | NIRA provides a process to request confirmation of information in its register; no public API specification was confirmed. Immigration publishes passport services; no external verification API was confirmed. |
| Rwanda | National Identification Agency (NIDA) — national identity cards | Directorate General of Immigration and Emigration (DGIE) | Official e-passport information confirms DGIE issuance. IREMBO is an application channel, not evidence of an external verification API. NIDA third-party verification API remains unconfirmed. |
| Ethiopia | National ID Program (NIDP) — Fayda digital identity | Immigration and Citizenship Service (ICS) | **Confirmed API candidate:** Fayda publishes authentication API information, OAuth 2.0/OIDC, e-KYC with holder OTP consent, and a partner portal for organizational onboarding. This is not a passport-verification API. |
| Botswana | Department of Civil and National Registration — Omang | Department of Immigration and Citizenship | Official government application services are published. No public external verification API was identified. |
| Zambia | Department of National Registration, Passport and Citizenship (DNRPC) — National Registration Card | Department of National Registration, Passport and Citizenship (DNRPC) | Ministry service pages identify both responsibilities. The DNRPC e-services portal has reported registration features under development; no external verification API was confirmed. |
| Namibia | Ministry of Home Affairs, Immigration, Safety and Security (MHAISS) — identity documents | MHAISS, Directorate of Visas, Permits, Passports and Citizenship | Official identity/passport services and a passport verification contact are published. A telephone contact is not an API; no machine-readable third-party API specification was confirmed. |
| United Republic of Tanzania | National Identification Authority (NIDA) — national identity cards | Tanzania Immigration Services Department | Government audit material confirms NIDA's population-register and ID-issuance responsibilities. The immigration e-portal supports passport applications and tracking. No external identity/passport verification API specification was confirmed in this batch. |

## Strongest API integration leads

### 1. Ethiopia — Fayda

Official sources:
- Authentication API and developer information: https://id.gov.et/authentication
- National ID Program overview: https://id.gov.et/about
- Organization partner portal: https://partner.fayda.et/

The official authentication page describes API integration, OAuth 2.0, OpenID Connect, partner onboarding, API documentation, and e-KYC. The described e-KYC flow uses a Fayda Alias Number (FAN) or Fayda Identification Number (FIN), with an OTP delivered to the holder for consent before e-KYC data is retrieved.

**Roadmap classification:** `API_DOCUMENTATION_PUBLISHED_PARTNER_ONBOARDING_REQUIRED`

**Important limitation:** this is a foundational resident digital identity authentication service. It must not be described as a passport service or as proof of citizenship. Exact data attributes, status checks, relying-party eligibility, and production endpoint contracts must be confirmed through partner documentation.

### 2. Ghana — NIA Identity Verification System

Official sources:
- Verification service and onboarding process: https://nia.gov.gh/service/verification-services/
- NIA official website: https://nia.gov.gh/

NIA describes real-time verification services for institutions. Its onboarding process requests institutional documentation, legal authority to collect personal data, data-protection certification, a description of intended use and data needs, technical setup, and an executed service contract.

**Roadmap classification:** `RESTRICTED_INSTITUTIONAL_SERVICE_CONTRACT_REQUIRED`

**Important limitation:** the public page documents an institutional service and onboarding process, not an unrestricted public API. Technical endpoint details and authentication must be obtained directly from NIA after approval.

### 3. South Africa — DHA National Population Register verification

Official source:
- https://www.gov.za/news/media-statements/home-affairs-launch-world-class-new-identity-verification-service-and-cost-effective-usage

The South African Government announced on 6 July 2025 that DHA had launched an identity-verification service allowing government and private-sector clients to verify information against the National Population Register.

**Roadmap classification:** `INSTITUTIONAL_VERIFICATION_SERVICE_API_DETAILS_TO_CONFIRM`

**Important limitation:** public announcement of a verification service does not provide sufficient evidence of public API availability, endpoint schemas, credentials, permitted queries, or integration eligibility.

## Important distinctions discovered

- A citizen-facing application portal is not automatically an API for third-party verification.
- An API that authenticates a resident digital identity is not necessarily a national ID card or passport validation API.
- A national identity authority and a passport authority may be separate institutions within the same country.
- A verification service may be restricted to institutions with legal authority and a signed agreement.
- A telephone, email, or contact form is an official contact channel, not a machine-readable API.
- A published application-tracking feature does not establish that an external party can query document authenticity or revocation status.

## Node Core OS mapping

The 22 issuer records have been entered into [ISSUER-AND-API-REGISTER.csv](ISSUER-AND-API-REGISTER.csv). Their Node Core OS capability mapping currently points to the planned catalogue capabilities for submitting verification requests and receiving authenticated institutional responses:

- `NCOS-ID-003` — submit an authorized verification request.
- `NCOS-ID-004` — receive and authenticate an institutional response.

These capability identifiers are planning references. They do not mean the Node Core OS endpoints or institution-specific connectors are implemented.

## Next research batch

Continue the African register systematically, prioritizing the remaining countries and areas in the geographic register. For each jurisdiction, identify the national identity issuer, passport authority, official legal mandate, official service URLs, verification mechanism, API documentation, access conditions, and source review date.

Do not set `AUTHORIZED_INTEGRATION_VALIDATED` until a connector has been tested with the institution's explicit authorization and reproducible evidence.
