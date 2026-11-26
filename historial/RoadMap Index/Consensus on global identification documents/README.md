# Consensus on Global Identification Documents

## 1. Purpose

This roadmap defines a worldwide identity and institutional-interoperability objective for Node Core OS byLAEV. It has two connected dimensions:

1. **A global identity layer:** design a persistent Node Core OS identity credential for a person and its associated network node, including people who lack official identity documents or whose nationality is unknown, undetermined, or not recognized.
2. **A lawful institutional pathway layer:** map and, where authorized, connect the competent public authorities and legally authorized organizations that can verify civil identity, issue documents, determine nationality, address statelessness, or process relevant residence and protection procedures.

The working name for the proposed network credential is **Node Core Global Identity Document (NC-GID)**. It would identify a person within the Node Core OS network. It would not, by itself, be a passport, a national identity card, proof of citizenship, or a grant of nationality. Only competent states and legally authorized institutions can make those determinations under applicable law.

The global mapping work is therefore broader than a directory of identity-card and passport issuers. It must establish a consistent path from the worldwide identity layer, through continents and jurisdictions, to the institutions and procedures that may lawfully help a person obtain recognition or documentation.

This is a roadmap requirement and a subject for research, specification, implementation, and validation. Its presence in this directory does not mean that NC-GID, global institutional connectivity, nationality pathways, or document verification are already implemented.

## 2. The minimum international requirement

Node Core OS must be designed with the capability to interoperate with the authorities and institutions responsible for issuing personal identification documents in different countries and jurisdictions.

At a minimum, the future system must provide a documented and versioned API architecture that can support authorized institutional connections, regardless of the country, jurisdiction, document format, or technical platform involved.

The framework must be extensible. It must not assume that every country has the same identity system, the same issuing authority, the same document types, or a publicly accessible verification API.

Where an institution does not provide an API, the roadmap must identify the official verification mechanism, access requirements, and any legal or technical limitations. Node Core OS must never represent an unavailable or unauthorized connection as an active integration.

## 3. The identity relationship to be established

The intended relationship consists of four distinct elements:

1. **Node:** a specific Node Core OS network node, identified by its technical node identifier.
2. **Person or subject:** the individual who declares and authorizes the association with that node.
3. **Identification document:** a personal identification document presented as evidence for that individual.
4. **Issuing institution:** the government authority or legally authorized institution that issued and delivered the document to its holder.

The intended association is:

**Node ↔ Person ↔ Identification Document ↔ Issuing Institution**

These links must be explicit, traceable, permission-controlled, and supported by evidence. A node identifier is a technical identity; it is not, by itself, proof of a person's civil or legal identity.

The system must preserve the distinction between a person's declaration, evidence supplied by that person, and confirmation received from the issuing institution.

## 4. Role of the Node Core OS network consensus

The Node Core OS network must be able to process and recognize identity-association claims according to a common protocol and shared verification rules.

In this context, network consensus is intended to establish agreement about the validity and provenance of a verification record according to the protocol's rules. It must not turn network participants into government identity issuers or give nodes authority to overrule the institution that issued a document.

The network must distinguish at least:

- A claim submitted by a node or person.
- Evidence presented by the person.
- The identity and authority of the claimed issuing institution.
- An institutional response, when an authorized verification channel exists.
- The scope and time of the checks actually performed.
- The resulting verification status and its cryptographic or auditable provenance.

A consensus result must never be interpreted as an institutional confirmation unless the issuing institution, or an officially recognized verification mechanism, actually supplied that confirmation.

The protocol must define how nodes validate the origin, integrity, freshness, and authorization of verification responses, and how they handle conflicting, unavailable, expired, revoked, or inconclusive results.

## 5. Institutional connectivity and APIs

Node Core OS must provide its own stable, documented APIs so external institutions and authorized integration services can communicate with the network.

The architecture should support:

- Institutional registration and identification.
- Issuer-directory discovery.
- Secure connector registration and configuration.
- Authentication of institutions and their services.
- Authorization scopes and permission management.
- Submission of document-verification requests.
- Delivery of institutional verification responses.
- Verification-result retrieval and status updates.
- Evidence and provenance references.
- Consent and authorization records.
- Audit events and traceability.
- Revocation, suspension, and connector deactivation.
- Version negotiation and compatibility management.

The design must also define the interfaces that an institution or its authorized service must expose. These may be APIs, signed credentials, official verification portals, secure message exchanges, or other documented mechanisms. The actual integration method must be determined separately for each institution.

Node Core OS must not assume that an institution permits arbitrary queries by document number. Access may require a legal basis, the person's authorization, institutional credentials, a formal agreement, approved purposes, or other conditions imposed by the authority.

## 6. Global issuer and institution directory

A central part of this work is the creation of a structured, maintainable directory of institutions that issue or administer personal identification documents.

The directory must be organized from the global level down to individual jurisdictions:

- World and geographic regions.
- Countries and territories.
- States, provinces, and other relevant jurisdictions.
- Government ministries, departments, agencies, civil registries, and legally authorized issuing institutions.
- Document categories and the institutions responsible for them.

The research must identify, where applicable:

- National identity card authorities.
- Passport issuing authorities.
- Civil registration authorities.
- Electronic identity and digital credential authorities.
- Residence and immigration document authorities.
- Regional or state-level identity document authorities.
- Other legally recognized personal identification issuers.

For each institution, the directory should record its official name, jurisdiction, legal mandate, official website, document types, verification mechanisms, API documentation, authentication requirements, permissions, access conditions, technical limitations, and the date and source of the latest confirmation.

The directory must distinguish the legal issuing authority from service operators, manufacturers, personalization contractors, and technology providers.

## 7. Verification requirements

The protocol must not treat all identity checks as one operation. It must distinguish:

1. **Issuer authority:** whether the institution is competent to issue the stated document.
2. **Document authenticity:** whether the document or credential can be confirmed as issued by that institution.
3. **Document status:** whether the document is current, expired, cancelled, suspended, or revoked, when the issuer can provide that information.
4. **Attribute correspondence:** whether the submitted attributes match the information held or confirmed by the institution.
5. **Holder binding:** whether the person presenting the document is its legitimate holder.

A valid document does not, by itself, prove that the person presenting it is the person to whom it was issued.

Each response must identify which checks were actually performed, by whom, through which authorized mechanism, and at what time. Unsupported checks must be reported as unavailable or inconclusive, never silently treated as successful.

## 8. Trust, permissions, and personal data protection

Institutional connectivity must be based on explicit trust relationships and controlled permissions.

The future design must address:

- Institutional authentication and service identity.
- Mutual authentication where technically supported.
- Least-privilege access scopes.
- Purpose limitation and legal authorization.
- Granular consent where consent is the appropriate legal basis.
- Secure transmission and protected credential storage.
- Signed or otherwise verifiable institutional responses.
- Replay protection, request identifiers, timestamps, and expiration.
- Rate limits, abuse prevention, and service availability.
- Auditability without unnecessary exposure of personal information.
- Retention, correction, revocation, and deletion requirements.

Personal identification documents and sensitive personal data must not be published to public or decentralized storage networks. Any use of local or distributed storage must be designed around data minimization, access control, encryption, and applicable law. Publicly visible hashes of predictable personal identifiers must not be used as a substitute for privacy protection.

## 9. Interoperability and network operation

The system must support different national systems and technical environments without requiring every institution to adopt an identical internal platform.

The roadmap must define common data schemas, API contracts, connector interfaces, error models, verification states, and protocol versions. Institution-specific differences should be handled by isolated connectors that translate official institutional mechanisms into the common Node Core OS protocol.

The design must account for:

- Different document formats and languages.
- Different national identifiers and data models.
- Institutions with public APIs, restricted APIs, or no API.
- Slow, unstable, or intermittent network connections.
- Timeouts, retries, rate limits, and partial responses.
- Temporary institutional outages.
- Protocol and schema version changes.
- Disagreement between sources and stale verification results.

A failed connection must never be interpreted as a positive verification. Retries must be bounded and safe, and the system must preserve enough information to explain why a result is pending or inconclusive.

## 10. Planned development work

The following work is pending and must be researched and specified before implementation:

- [ ] Define the global geographic and jurisdictional coverage.
- [ ] Build the worldwide inventory of personal identification document issuers.
- [ ] Identify the issuing authorities for national identity documents and passports in each jurisdiction.
- [ ] Research official institutional APIs and alternative verification mechanisms.
- [ ] Record institutional access rules, legal requirements, and integration procedures.
- [ ] Audit existing Node Core OS identity, node, entity, evidence, and permission capabilities.
- [ ] Define the common identity-association data model.
- [ ] Define the institutional issuer registry schema.
- [ ] Specify the Node Core OS institutional API.
- [ ] Specify the institutional connector interface.
- [ ] Specify authentication, authorization, consent, and audit requirements.
- [ ] Define verification request and response schemas.
- [ ] Define network-consensus rules for identity-association and verification records.
- [ ] Define conflict resolution, revocation, expiration, and stale-result handling.
- [ ] Build test connectors using fictitious identities and test documents.
- [ ] Validate connector behavior under slow, unreliable, and interrupted network conditions.
- [ ] Establish a pilot integration with an institution only after obtaining the required authorization.
- [ ] Document interoperability and security test results.

## 11. Expected deliverables

This work may produce the following documentation and implementation artifacts as the research progresses:

- Global jurisdiction and issuer map.
- Global issuer registry.
- Institutional API and verification-mechanism inventory.
- Identity-association architecture.
- Node Core OS institutional API specification.
- Institutional connector specification and development guide.
- Identity permissions and consent model.
- Verification request and response protocol.
- Network-consensus rules for identity-association records.
- Security, privacy, and threat model.
- Test plan and reproducible test fixtures.
- Institution-specific connector implementations, where authorized.
- Integration and validation reports.

These are planned deliverables, not claims that the files, APIs, connectors, or integrations already exist.

## 12. Completion criteria

This roadmap item can only be considered complete when:

- The intended geographic and institutional coverage is documented.
- Issuing authorities are supported by reliable, preferably official, sources.
- Institutional APIs and verification methods are accurately classified by access level and availability.
- The Node Core OS API and connector contracts are specified and versioned.
- Identity associations preserve the distinction between node, person, document, and issuer.
- Verification responses have authenticated provenance and clearly defined scope.
- Network consensus cannot convert an unverified claim into an institutional confirmation.
- Privacy, authorization, and data-retention controls are documented and tested.
- Test connectors pass reproducible tests, including failure and low-bandwidth scenarios.
- Real institutional integrations are tested only with appropriate authorization and documented evidence.

## 13. Guiding principle

Node Core OS byLAEV aims to provide a decentralized technical infrastructure through which a person can maintain a persistent global identity within the network, associate that identity with a Node Core OS node, preserve verifiable evidence, and connect with competent institutions through lawful and authorized procedures.

The proposed NC-GID is a network-issued identity credential. It can support continuity of identity and evidence management, including for people who do not currently possess official identity documents. It must clearly distinguish self-declared information, submitted evidence, corroborated information, issuer-verified data, and legal status determined by a competent authority.

Node Core OS cannot grant citizenship, assign a nationality, issue a government identity document, or compel a state to recognize a credential. Its role is to help organize evidence, identify potentially relevant jurisdictions and institutions, support authorized verification, and facilitate lawful referral and application pathways. A state authority retains responsibility for decisions about nationality, civil status, and its own documents.

**The goal is not to replace national identity systems. The goal is to provide a global identity layer that can connect people and their evidence to the competent national and institutional systems, while respecting each institution's legal authority.**

## 14. Global mapping strategy: from macro to micro

“Macro to micro” describes the complete identity and recognition pathway that Node Core OS intends to support. It is not only a geographic directory of document issuers. The global database must make it possible to start from a worldwide identity framework, locate the relevant continental and national structures, identify the institutions with legal competence, and connect an individual and their node to the appropriate lawful procedures.

The mapping must support two complementary directions:

- **Global to individual:** define the worldwide network, its regions, jurisdictions, institutions, APIs, and procedures so that a person can be routed to the relevant authority.
- **Individual to institution:** start from a person and their Node Core OS node, organize available evidence, identify possible jurisdictional links, and determine which competent institutions may assess identity, nationality, documentation, or protection claims.

### 14.1 The macro-to-micro hierarchy

1. **World — global identity layer:** define the worldwide NC-GID framework, the common identity model, network-wide rules, and the directory of jurisdictions and institutions. The global credential is intended to provide persistent identity within Node Core OS without assuming that a person already has a nationality or government document.
2. **Continents and geographic regions:** organize the global structure into consistent regional groupings. This layer supports coverage planning, regional interoperability, research, and future cooperation between institutions.
3. **Countries and jurisdictions:** map countries, territories, and relevant subnational jurisdictions. For each one, research the legal framework and official procedures concerning civil registration, nationality, identity documents, passports, residence, immigration, asylum, refugee protection, and statelessness, where applicable.
4. **Competent institutions and authorized organizations:** identify, by legal mandate, the institutions that can issue or verify identity documents, register births and civil events, determine or confirm nationality, process immigration or protection matters, assess statelessness where such a procedure exists, and provide legally authorized support or referrals. Record their official services, APIs, access rules, and contact or application channels.
5. **Person and Node Core OS node — individual level:** associate a person with a persistent NC-GID and a technical node identity; record claims and evidence with explicit provenance and protection; map possible links to countries or jurisdictions; and support referrals or applications to the competent institutions. A node identifier is not, by itself, proof of civil identity or nationality.

The institutional levels and the individual level must remain distinct. A person is not assigned a nationality by the network. The system helps identify and document a possible lawful pathway; the competent authority evaluates the case and makes the decision.

### 14.2 Global identity credential and its limits

The proposed **Node Core Global Identity Document (NC-GID)** is a credential issued by the Node Core OS network for identity continuity inside that network. Its design should address:

- A unique, opaque global identity reference that does not expose a government identifier.
- A verifiable link between the person, the NC-GID, and one or more Node Core OS nodes, with recovery and transfer rules defined separately.
- Clear provenance for information: self-declared, evidence-submitted, independently corroborated, institution-verified, or legally determined.
- Evidence references, verification history, consent or other lawful authorization, validity, suspension, and revocation.
- A way to link official national documents or institutional credentials when they are later obtained or verified.
- Protection against duplicate identities, impersonation, coercion, unauthorized correlation, and harmful disclosure.

NC-GID must never be represented as a government-issued identity document, passport, proof of citizenship, travel authorization, or guarantee of recognition by a state. Any external recognition would require a separate legal basis or agreement with the competent institution.

### 14.3 Distinguishing identity and nationality situations

The database and protocol must not collapse different legal and documentary situations into one category. At minimum, distinguish:

- **Undocumented person:** a person who lacks documents or cannot currently produce evidence of identity or nationality. This fact alone does not establish statelessness.
- **Nationality not yet determined:** available information is insufficient to establish whether a person holds a nationality.
- **Nationality claimed or potentially supported:** a person declares a nationality or presents evidence that may support a claim, but the competent authority has not confirmed it.
- **Nationality confirmed:** a competent state authority or legally recognized source has confirmed the relevant nationality.
- **Statelessness formally recognized:** stateless status has been determined by a competent authority under the applicable legal procedure.
- **Statelessness suspected or under assessment:** a concern is being examined, but there has been no formal determination.

These are not interchangeable labels. Node Core OS must record who made a determination, under which procedure, on what date, and with what evidence. The network must not independently declare a person stateless or assign a nationality.

### 14.4 Jurisdiction and lawful pathway research

For each country or jurisdiction, the global database should gradually identify the authorities and procedures relevant to a person's circumstances, including where they exist:

- Civil registration and birth registration authorities.
- Nationality, citizenship, and naturalization authorities.
- National identity-document issuing authorities.
- Passport issuing authorities.
- Immigration, residence, and migration-status authorities.
- Asylum and refugee-protection authorities.
- Statelessness determination bodies or procedures.
- Courts, ombuds institutions, or administrative review bodies where they have a relevant legal role.
- UN agencies, humanitarian organizations, legal-aid providers, and civil-society organizations, but only with their role and authority accurately classified.

For every institution, the database must state its actual mandate. An organization that provides assistance or referrals must not be described as having authority to grant nationality or issue a state document unless that authority is established by law.

Research should identify official procedures and potential legal routes, not promise that a person qualifies for a status or that a state will accept an application. Possible links may include birth on a territory, parentage, previous nationality, residence, family ties, or other grounds recognized by the relevant country's law. These are research indicators, not automatic legal conclusions.

### 14.5 Geographic baseline and institutional database

Use a recognized and maintainable geographic classification as the baseline. The United Nations Statistics Division M49 standard is a suitable reference because it organizes countries or areas under geographic regions and subregions.

Reference: https://unstats.un.org/unsd/methodology/m49/

M49 is used for consistent geographic indexing. It is not a legal determination of sovereignty, statehood, borders, citizenship, or institutional authority. Preserve the distinction between sovereign states, territories, and other areas, and add subnational jurisdictions when they are necessary to identify the competent institution.

The existing 248-record country-and-area geographic register remains the foundation of the worldwide database. The existing identity-document and passport issuer register also remains useful and must continue to be researched. It is the first institutional dataset, not the full scope of the project.

As the database develops, expand it to include the additional institution categories in Section 14.4. Each institution should have its own record and a clear relationship to its jurisdiction, legal mandate, service or procedure, and API or other access channel. Where one institution performs several roles, record each role separately rather than assuming that all functions are identical.

### 14.6 Institution and API mapping

For each institution or authorized service, document two sides separately.

**A. Official institution-provided service**
- Official name and responsible institution.
- Legal mandate and jurisdiction.
- Service, procedure, or document category.
- Official API or service name and documentation URL, if available.
- Sandbox or test environment, if available.
- Authentication, eligibility, consent, and authorization requirements.
- Legal agreements, fees, usage limits, and data-access restrictions.
- Alternative official methods where no API exists, such as an application portal, formal request, or in-person process.
- Source references and date last checked.

**B. Node Core OS interface**
- The Node Core OS API capability required for the connection.
- The planned endpoint, connector, or protocol identifier once specified.
- The Node Core OS specification link.
- Implementation, testing, and authorization status.

Never invent an institutional URL or Node Core OS endpoint. Keep planned Node Core OS interfaces marked as pending until they have actually been specified and implemented. A public website, contact form, or citizen application portal is not automatically an API.

### 14.7 Individual-to-institution workflow

The intended workflow for a person who lacks official documents or whose nationality is unresolved is:

1. Create or associate a persistent NC-GID with the person's Node Core OS identity and node, without presuming nationality.
2. Record the person's declarations and available evidence with explicit source, date, consent or other legal authorization, and confidence status.
3. Identify potential jurisdictional links from evidence such as birth, parentage, residence, family records, or prior documents. Treat these as leads for review, not as legal determinations.
4. Identify the competent civil-registration, nationality, immigration, protection, or statelessness institutions for the relevant jurisdictions.
5. Present the person with the official procedure and authorized contact or application path, or connect through an institutional API only where permitted.
6. Record submissions, institutional responses, pending steps, and decisions with verifiable provenance.
7. When an authority confirms a nationality or issues a government document, associate that verified result with the NC-GID without replacing the original institutional record.

Network consensus may validate the integrity and provenance of records according to the protocol. It cannot replace an authority's legal evaluation or convert an unverified claim into a government determination.

### 14.8 Evidence, privacy, and storage

The worldwide public mapping database should contain institutional and procedural information, not personal case files. Real identity documents, biometric data, personal identifiers, and sensitive evidence must not be placed in public repositories, public IPFS gateways, or public ledgers.

Personal evidence, where the project is legally permitted to process it, requires data minimization, encryption, access control, clear retention rules, and a lawful basis. Public hashes of predictable personal identifiers are not an adequate privacy measure. The storage architecture must distinguish public institutional metadata from protected personal records and cryptographic proofs.

The project should begin with transparent, synthetic test data while the data model and access controls are validated. Real-person processing must be introduced only after privacy, legal, and security requirements are established.

### 14.9 Research and implementation sequence

1. Maintain the global geographic index and its source references.
2. Continue country-by-country research into national identity and passport issuers already represented in the database.
3. Add civil-registration and birth-registration authorities.
4. Add nationality and naturalization authorities and document official procedures.
5. Add immigration, asylum, refugee-protection, and statelessness-related authorities or procedures where applicable.
6. Identify authorized support organizations separately from government decision-makers.
7. Record official APIs, restricted services, portals, application channels, and non-digital procedures accurately.
8. Specify the NC-GID data model and the distinction between claims, evidence, verification, and legal determinations.
9. Specify institutional APIs, connector interfaces, permissions, and auditable response formats.
10. Test with synthetic data and authorized sandbox environments, including slow, unreliable, and interrupted network conditions.
11. Establish real integrations only after the required authorization and legal basis are obtained.
12. Review sources, statuses, and institutional changes periodically.

### 14.10 Mapping status and evidence

Every record must have a research status, source references, and a last-reviewed date. At minimum, distinguish: not researched, research in progress, institution identified, legal mandate confirmed, procedure researched, API or mechanism researched, access requirements confirmed, connector specified, sandbox tested, and authorized integration validated.

Also distinguish a confirmed institution with no known API, an API that is restricted, an unavailable service, and a service whose existence has not been confirmed. These conditions must never be presented as equivalent.

### 14.11 Working files

The operational geographic and institutional mapping files are maintained in the [GLOBAL-MAPPING](GLOBAL-MAPPING/README.md) directory:

- [Global Mapping Strategy](GLOBAL-MAPPING/README.md)
- [Continental and Geographic Region Index](GLOBAL-MAPPING/CONTINENT-INDEX.md)
- [Complete Countries and Areas by Continent](GLOBAL-MAPPING/COUNTRIES-AND-AREAS-BY-CONTINENT.md)
- [Country and Jurisdiction Register](GLOBAL-MAPPING/COUNTRY-AND-JURISDICTION-REGISTER.csv)
- [Issuer and API Register](GLOBAL-MAPPING/ISSUER-AND-API-REGISTER.csv)
- [Institution Research Template](GLOBAL-MAPPING/INSTITUTION-RESEARCH-TEMPLATE.md)
- [Node Core OS API Capability Catalogue](GLOBAL-MAPPING/NODE-CORE-OS-API-CATALOG.md)

These files establish the structure for collecting verified information. The geographic inventory is populated, but the institutional and legal-pathway database remains a work in progress. Country and institution records must be expanded through documented research.

