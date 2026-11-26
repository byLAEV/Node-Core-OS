# Global Mapping Mission and Requirements

## 1. Mission

The worldwide mapping work is not merely a directory of countries, institutions, identity documents or civil registries. It is the institutional and legal knowledge infrastructure that enables Node Core OS byLAEV to help people preserve identity evidence, understand possible legal pathways, and locate the authorities competent to address their circumstances.

The core problem is that people without identity documents, people whose nationality is unknown or disputed, and people at risk of statelessness may be unable to access the very institutions and procedures that could help establish or document their legal identity.

Node Core OS must therefore map the institutional environment before it can responsibly guide a person through it.

## Immediate mapping priority — identity and passport issuers

The current foundational mapping phase has a narrower and measurable objective: for every applicable country, territory or jurisdiction in the geographic baseline, identify the institution that issues identity documents and the institution that issues passports or state travel documents, together with each institution's official website or direct official service page.

This phase includes all continental groups, special administrative regions and territories with distinct issuing authorities. It also maintains a separate register for global, regional and non-territorial organizations that issue restricted official travel documents. Those documents must not be counted as ordinary national passports.

The broader research domains below remain future layers. They do not replace or delay completion of the issuer directory. API discovery and connector implementation are explicitly deferred until the issuer directory is established.

See [Issuer Mapping Scope and Coverage Rules](ISSUER-MAPPING-SCOPE-AND-COVERAGE.md) and the [Global Identity and Passport Issuer Master Register](GLOBAL-IDENTITY-AND-PASSPORT-ISSUER-MASTER-REGISTER.csv).

## 2. Scope of the problem

A person may:
- Never have had a birth registered.
- Have lost all identity documents.
- Have been born in a country different from the country of either parent.
- Not know the nationality or civil-registration history of their parents.
- Have family links to multiple countries.
- Have errors or inconsistencies in civil or identity records.
- Be unable to locate records because archives were lost, destroyed or reorganized.
- Have no nationality recognized by any State, or be unable to establish whether a nationality exists.
- Not know which institution has authority to assist.

Lack of documents must never automatically be classified as statelessness. The system must distinguish lack of evidence, undocumented nationality, disputed nationality, undetermined nationality and legally recognized statelessness.

## 3. Macro-to-micro institutional map

The map must represent the following hierarchy and relationships:

1. **World and international framework** — global organizations, conventions, standards and international protection mechanisms.
2. **Continents and regions** — regional organizations, legal frameworks and cooperation mechanisms.
3. **Countries, territories and jurisdictions** — applicable legal systems, territorial scope and jurisdictional status.
4. **Institutions** — civil registration, national identity, nationality and naturalization, justice, interior, foreign affairs, immigration, asylum, refugee protection and statelessness authorities.
5. **Offices and operational units** — local registries, municipal offices, regional directorates, consulates, courts, commissions, archives and service desks.
6. **Competencies and procedures** — legal mandate, decision-making power, intake, investigation, evidence requirements, deadlines, appeals, review and referral.
7. **Person-facing pathways** — documented routes for birth registration, late registration, record recovery, correction, proof of parentage, nationality recognition, naturalization, identity documents, travel documents and protection.

The map must distinguish a final legal decision-maker from an intake office, technical processor, archive, supporting organization or referral service. Parent-child relationships between institutions must be explicit where supported by sources.

## 4. Person-centred use cases

The map must support future applications and workflows including:

- **Birth Recovery:** locating birth-registration authorities, late-registration procedures and archival records.
- **Nationality Pathway:** identifying possible nationality by birth, descent, adoption, marriage or naturalization, subject to applicable law and facts.
- **Family Lineage:** reconstructing legally relevant family relationships and identifying records held in different jurisdictions.
- **Statelessness Assistance:** locating statelessness determination procedures, protection institutions and legal-aid referrals.
- **Civil Identity Recovery:** recovering, replacing or correcting civil-status and identity documents.
- **Identity Evidence Verification:** recording provenance, integrity, corroboration and authorized institutional confirmation.

These applications should share the same normalized geographic, institutional, legal, documentary and procedural knowledge base rather than create isolated country directories.

## 5. Evidence-to-institution pathway

For a future person-authorized workflow, Node Core OS should be able to:

1. Identify the jurisdictions potentially connected to the person's circumstances.
2. Identify the applicable laws and relevant dates.
3. Identify institutions that hold or can certify relevant records.
4. Identify the records and evidence that may be required.
5. Identify procedures for registration, recovery, correction, nationality determination or protection.
6. Identify the competent decision-maker and any appeal or review mechanism.
7. Produce a sourced, versioned pathway with unresolved questions clearly marked.
8. Refer the person to competent authorities or qualified legal assistance where appropriate.

A suggested pathway is informational support, not a legal determination or guarantee of a result.

## 6. Decentralized node relationship and trust boundaries

A personal node may preserve a person's account of their history and evidence even when the person has no state-issued identity document. Other nodes may corroborate limited claims or attest to the integrity and provenance of records under explicit rules.

However:
- Peer corroboration does not itself establish civil status, parentage or nationality.
- Cryptographic integrity does not prove that a statement is true.
- A network credential does not become a government identity document.
- Only the competent State authority can make the legal determination assigned to it by law.
- External institutional verification requires a lawful basis, appropriate authorization and any required consent.
- Public repositories, public IPFS networks and public blockchains must not contain personal identity documents, raw personal data or reusable hashes of personal identifiers.

The future global Node Core credential may identify a node and preserve continuity within the network. It must be clearly distinguished from a national identity card, passport, residence permit, refugee document or proof of citizenship.

## 7. Institutional mapping requirements

A jurisdiction is not considered fully mapped merely because a country name or national ID issuer is listed. Research must identify, where applicable:

- Civil-status and birth-registration authorities.
- Nationality, citizenship and naturalization authorities.
- National identity and population-register authorities.
- Passport and travel-document authorities.
- Immigration, residence and border authorities.
- Asylum and refugee-status authorities.
- Statelessness determination and protection authorities.
- Courts and administrative review bodies relevant to the procedures.
- Archives and record custodians.
- Consular and diplomatic authorities.
- Legal-aid and authorized civil-society referral organizations.
- Regional and local offices that actually receive or process applications.

For each record, capture its jurisdiction, parent institution, legal mandate, operational function, decision-making role, procedures, required evidence, deadlines, appeal route, official source, source date, review date and confidence/status.

Where a function has not been researched, mark it **NOT_RESEARCHED**. Do not infer that an institution or procedure does not exist merely because no record has been found. Use **NOT_APPLICABLE** only when a reliable source or the legal/territorial framework supports that conclusion.

## 8. Source and verification policy

Prioritize:
1. Current legislation, regulations and official gazettes.
2. Official institutional websites, service guides, forms and directories.
3. Official regional and international organization sources.
4. Credible secondary sources for context or discovery, clearly labelled as secondary.

Every material institutional or procedural claim must be traceable to a source. Record when it was checked. Distinguish a law that establishes a mandate from a website that describes current operations. Flag conflicts, outdated pages, missing appeals information and uncertain operational arrangements.

## 9. API and connector sequencing

The institutional map must be built first. API discovery, integration, authentication, connector implementation and automated data exchange are a later phase.

An official online form, telephone number, email address, public service portal or permission to submit electronically is not evidence that a public API exists. API availability and third-party access must be separately researched and documented after the relevant institution, competence and lawful purpose are understood.

The API catalogue is therefore a deferred planning layer, not the current mapping objective.

## 10. Completion criteria

The worldwide mapping phase is complete only when:

- All continents and regions are represented.
- All countries, territories and relevant jurisdictions in the selected geographic baseline are accounted for.
- Institutional coverage has been researched function by function.
- Relevant national and subnational offices are identified to a useful operational level.
- Institutional parent-child and cross-jurisdiction relationships are represented.
- Legal mandates, procedures, evidence requirements, deadlines and review mechanisms are documented where available.
- Official sources and review dates are recorded.
- Unknown, partial, conflicting and non-applicable data are explicitly distinguished.
- The normalized data can be consumed by multiple Node Core OS applications.
- Data protection, consent, access control and retention boundaries are documented before any real personal data or external integration is used.

## 11. Foundational principle

A person should be able to begin preserving their identity history and evidence without first possessing a state-issued identity document. Node Core OS can help preserve that history and identify possible routes toward legal recognition. The worldwide institutional map connects that evidence to the laws, institutions and procedures that may be able to act on it.

**The purpose is not to replace public authorities. It is to make the world's identity-related institutional infrastructure navigable, traceable and usable by people who otherwise may not know where to begin.**


## 2. Global functional infrastructure

The worldwide map is not limited to personal identity and nationality. It is a reusable knowledge infrastructure through which Node Core OS nodes can discover the official information, institutions, services, eligibility rules and procedures relevant to a person's needs in any mapped jurisdiction.

The map is organized into functional domains that share the same geographic and institutional backbone:

1. **Identity, civil status and nationality** — birth registration, civil records, identity documents, nationality by descent or birth, naturalization, statelessness safeguards and legal remedies.
2. **International travel** — entry conditions, visa and transit rules, passport validity, travel-document recognition, permitted stay, border requirements and official consular guidance. Requirements must be evaluated against the traveler's nationality, document type, residence, purpose, route and travel dates.
3. **Residence and migration** — visas, residence permits, work authorization, family reunification, study routes, permanent residence, renewals, regularization and appeal procedures.
4. **Education** — admission authorities, accreditation, recognition of prior qualifications, credential equivalency, student visas, scholarships and public education access requirements.
5. **Work and professional access** — work permits, regulated-profession licensing, qualification recognition, labor registration, social-security enrollment and official employment services.
6. **Public and essential services** — the competent authorities and access rules for services that are relevant to a person's legal and practical situation, mapped only where an authoritative source and a clear use case exist.
7. **Institutional and digital access** — official portals, documented APIs, authentication methods, eligibility, consent, legal basis, access agreements, service availability and technical limitations. This is a later integration layer, not permission to access restricted systems.

For each domain, the map must distinguish the rule-making authority, legal decision-maker, service operator, local office, appeal body and information-only source. An online form or portal must never be labelled an API unless a technical interface and authorized access conditions are documented.

## 3. Shared data model and domain-specific extensions

All domain records must reference the same canonical geography and jurisdiction identifiers. Institution records must use stable institution IDs; procedures must reference the competent institution and, where known, the actual decision-maker. Domain-specific registers may be added without duplicating the geographic baseline.

A domain record should capture, as applicable: jurisdiction, scope, responsible authority, service/procedure, eligible persons, required evidence, fees, deadlines, exceptions, appeal/review route, official source, date last checked, evidence confidence, language/accessibility, online/offline channel, and unresolved questions. Travel and migration records additionally require effective dates and nationality/document-specific conditions. Education and work records require qualification, occupation, accreditation or licensing context where relevant.

Unknown information must remain explicitly unknown (for example, NOT_RESEARCHED or SOURCE_REVIEW_REQUIRED). It must not be inferred from the absence of a record.

## 4. Mapping sequence and API boundary

The work proceeds in this order:

1. Complete the geographic and jurisdiction baseline.
2. Map the institutional hierarchy and legal competences.
3. Map procedures and services by functional domain, beginning with identity and nationality while expanding to travel, migration, education and work.
4. Record official sources, effective dates, evidence quality and unresolved gaps.
5. Review coverage and validate cross-jurisdiction relationships.
6. Only after the relevant domain and institution are mapped, assess APIs and digital integrations individually for documented technical capability, lawful purpose, authorization, consent and security.

The API catalogue is therefore a planning inventory until each interface is independently documented and approved for use. No public API, third-party access right or government recognition may be inferred from a website, portal, document or institutional listing.
