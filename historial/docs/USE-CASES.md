# Node Core OS — Master Catalog of Use Cases, Protocols, and Applications

**Status:** Reference architecture / proposed use-case catalog.

> This catalog describes architectural possibilities. A listed NC-* application is not, by its presence here, a claim that it is implemented, audited, certified, or deployed in production.

## 1. Platform thesis
Node Core OS combines node infrastructure, local storage, decentralized storage such as Kubo/IPFS, and reusable trust/evidence protocols. These protocols can be composed into domain applications.

NODE CORE OS → CORE INFRASTRUCTURE → TRUST PROTOCOLS → DOMAIN APPLICATIONS

The same infrastructure can support different sectors while changing requirements, evidence types, issuers, policies, temporal rules, proof rules, and governance.

## 2. Architectural levels
### Level 1 — Core infrastructure
- Local storage; Kubo/IPFS; networking; cryptographic keys and signatures; CIDs; node lifecycle; identity primitives.

### Level 2 — Trust and evidence protocols
- NC-ID; NC-EVIDENCE; NC-REQUIREMENT; NC-REMEMBER; NC-PROVENANCE; NC-REPUTATION; NC-SOURCEDIVERSITY; NC-TEMPORAL; NC-NULLIFIER; NC-REVOCATION; NC-PROOF; NC-POLICY; NC-AUDIT; NC-GOVERNANCE.

### Level 3 — Vertical applications
An NC-* application composes core capabilities, trust protocols, domain logic, policy, and governance.

## 3. Common operational pattern
REQUEST → REQUIREMENT → POLICY → CURRENT CONTEXT → REMEMBER IF NEEDED → MINIMUM NECESSARY HISTORY → EVIDENCE → CORROBORATION / SOURCE DIVERSITY → TEMPORAL CHECKS → PROOF → DECISION → MINIMUM CONTEXT RELEASE → FORGOTTEN

FORGOTTEN means historical context is inactive by default. It does not mean deletion, destruction, or loss of evidence. STORE ≠ REMEMBER ≠ USE ≠ SHARE ≠ PUBLISH ≠ AUTHORIZE ≠ PURGE.

## 4. Data, evidence, proof, and decision
Historical Data ≠ Evidence ≠ Proof ≠ Decision.
Historical data is what exists in the node or trusted sources. Evidence is the relevant subset supporting a claim. Proof is a verifiable demonstration under a defined cryptographic and trust model. Decision is the policy interpretation of that proof.

Zero-knowledge proofs can minimize disclosure, but they do not independently prove that an underlying real-world fact is true. Issuers, provenance, trust roots, source completeness, and governance remain important.

## 5. Sector catalog

### Enterprise and procurement
Applications: NC-SUPPLIER, NC-VENDOR-RISK, NC-CONTRACT, NC-PROCUREMENT, NC-ERP, NC-HR.
Uses: supplier eligibility, contractor onboarding, contract compliance, vendor risk, employee credentials, and inter-company attestations. A buyer can request proof of selected requirements without receiving the complete historical dossier.

### Finance and fintech
Applications: NC-BANK-KYC, NC-AML, NC-CREDIT, NC-LENDING, NC-PAYMENTS, NC-FINANCE.
Uses: selected eligibility proofs, financial attestations, collateral evidence, contractual obligations, issuer attestations, temporal validity, revocation, and selective disclosure. Regulated controls remain necessary.

### Government and public administration
Applications: NC-GOV, NC-PUBLIC-SERVICE, NC-BENEFIT, NC-TAX, NC-PERMIT, NC-LICENSE, NC-INTEROPERABILITY.
Uses: permit validity, public-service eligibility, licenses, credentials, and inter-agency evidence exchange. Legal authority, due process, accessibility, human review, correction, and appeal are required.

### Civic and electoral systems
Applications: NC-ELECTOR-ID, NC-VOTING-PARTICIPATION, NC-DEMOCRATIC-GOVERNANCE.
Uses: eligibility evidence, duplicate-participation prevention, credential verification, and auditability while separating eligibility from ballot secrecy. An anomaly must not automatically become an accusation; institutional authority, independent auditing, privacy, transparent rules, and review are required.

### Education and professional credentials
Applications: NC-CREDENTIAL, NC-UNIVERSITY, NC-TRAINING, NC-CONTINUING-EDUCATION, NC-PROFESSIONAL-LICENSE.
Uses: diploma and certification verification, continuing education, professional licensing, current status, and revocation without exposing unrelated academic history.

### Health and medical credentials
Applications: NC-HEALTH, NC-MEDICAL-CREDENTIAL, NC-PROVIDER, NC-INSURANCE.
Uses: professional authorization, narrow eligibility proofs, credential validity, and controlled evidence exchange. Health deployments require strict privacy, consent, access control, legal compliance, retention, emergency procedures, and correction.

### Insurance
Applications: NC-INSURANCE, NC-CLAIMS, NC-RISK.
Uses: policy validity, incident evidence, claims documentation, provenance, corroboration, and auditable adjudication. Evidence collection should remain distinct from final adjudication and appeal.

### Supply chain, logistics, and cargo
Applications: NC-SUPPLY-CHAIN, NC-LOGISTICS, NC-CARGO, NC-PORT, NC-TRADE.
Uses: shipment provenance, custody transitions, inspections, certifications, delivery attestations, and cross-organization verification. Temporal coherence and independent source corroboration are useful here.

### Pharmaceutical and food provenance
Applications: NC-PHARMA, NC-FOOD, NC-COLD-CHAIN, NC-PRODUCT-PROVENANCE.
Uses: manufacturing, inspection, authorization, custody, temperature evidence, origin, and certification. Cryptography protects provenance integrity but does not replace physical inspection or trusted measurement.

### Agriculture
Applications: NC-AGRI, NC-FARM, NC-LAND-PROVENANCE, NC-FOOD-ORIGIN.
Uses: production events, origin, certifications, inspections, custody, and market-specific evidence.

### Energy and utilities
Applications: NC-ENERGY, NC-WATER, NC-GRID, NC-UTILITY.
Uses: equipment certification, maintenance, inspections, operator credentials, service events, authorization states, and multi-operator evidence exchange.

### Industrial, manufacturing, and IoT
Applications: NC-MANUFACTURING, NC-IOT, NC-ROBOTICS, NC-DIGITAL-TWIN, NC-SMART-FACTORY, NC-INDUSTRIAL-COMPLIANCE.
Uses: device identity, firmware provenance, maintenance history, authorization, approved configurations, and auditable industrial events.

### Software and digital supply chains
Applications: NC-SOFTWARE-SUPPLY-CHAIN, NC-SOFTWARE-PROVENANCE, NC-BUILD-ATTESTATION, NC-DOCUMENT, NC-CONTENT-PROVENANCE.
Uses: source-to-build provenance, dependency policy, release attestations, document integrity, and version verification.

### Artificial intelligence and autonomous agents
Applications: NC-AI, NC-AI-AGENT, NC-AI-AGENT-NETWORK, NC-MODEL-PROVENANCE, NC-AGENT-AUTHORITY.
Uses: agent identity, credentials, task requirements, action limits, provenance, spending limits, audit evidence, and proofs that an action is within policy. Human and agent identities should remain distinct unless explicitly governed.

### Legal, compliance, and audit
Applications: NC-LEGAL, NC-COMPLIANCE, NC-AUDIT, NC-CASE-EVIDENCE, NC-ATTESTATION.
Uses: evidence provenance, attestations, versions, policy evaluations, audit trails, and controlled historical access. Jurisdiction-specific rules and professional oversight remain necessary.

### Real estate and property
Applications: NC-REALTY, NC-PROPERTY, NC-LEASE, NC-ASSET-PROVENANCE.
Uses: deeds, inspections, permits, leases, maintenance events, property provenance, and transaction-specific proofs.

### Infrastructure, cities, and public works
Applications: NC-SMART-CITY, NC-INFRASTRUCTURE, NC-PUBLIC-WORKS, NC-ASSET-MAINTENANCE.
Uses: construction, inspection, maintenance, certification, contractor evidence, and public-asset provenance.

### Decentralized organizations and P2P networks
Applications: NC-P2P, NC-CONSORTIUM, NC-DAO, NC-DISTRIBUTED-ORGANIZATION, NC-GOVERNANCE.
Uses: participation rights, delegation, attestations, proposal eligibility, action authorization, nullifiers, and dispute-aware governance.

### Scientific and research collaboration
Applications: NC-RESEARCH, NC-DATA-PROVENANCE, NC-LAB, NC-RESEARCH-CREDENTIAL.
Uses: dataset provenance, experiments, instrument attestations, authorship, analysis artifacts, and verification without exposing confidential raw data.

### Media, creative work, and intellectual property
Applications: NC-CREATOR, NC-CONTENT-PROVENANCE, NC-LICENSE, NC-IP.
Uses: provenance, licensing relationships, version history, authorship attestations, and license verification.

## 6. Reusable protocol composition
| Protocol | Primary role |
|---|---|
| NC-ID | Identity and key relationships |
| NC-EVIDENCE | Structured evidence and claims |
| NC-REQUIREMENT | Formalizes what must be demonstrated |
| NC-REMEMBER | Activates minimum necessary historical context |
| NC-PROVENANCE | Tracks origin and lineage |
| NC-REPUTATION | Derives contextual reputation |
| NC-SOURCEDIVERSITY | Evaluates independent source corroboration |
| NC-TEMPORAL | Validity and temporal coherence |
| NC-NULLIFIER | Prevents defined duplicate or reuse conditions |
| NC-REVOCATION | Invalidates credentials or states |
| NC-PROOF | Produces verifiable claims, potentially with ZK |
| NC-POLICY | Defines decision rules |
| NC-AUDIT | Records accountable decision trails |
| NC-GOVERNANCE | Defines authority, review, disputes, and policy control |

## 7. Standard application template
Every future NC-* application should document: problem, actors, requirements, evidence, issuers, protocols, memory policy, proof policy, decision model, governance, privacy, revocation, threat model, and status.

## 8. Reference implementation strategy
Core Storage / Runtime → Content + Identity → Evidence + Requirement → REMEMBER + Policy → Provenance + Temporal + Source Diversity → Proof + Revocation + Nullifiers → Reference Application → Additional verticals.

NC-SUPPLIER is a strong reference application because it exercises identity, evidence, requirements, selective memory, corroboration, source diversity, temporal validity, contextual reputation, proof, audit, and policy without requiring every vertical to be solved simultaneously.

## 9. Architectural limits
- Cryptographic control of a key does not by itself prove a unique physical person.
- A Merkle proof proves inclusion in a committed structure, not truth in the physical world.
- A ZK proof proves a statement relative to its circuit, inputs, and trust assumptions.
- Absence from a local database is not proof of absence from the world.
- Source diversity must consider independence, not only record count.
- Reputation is contextual and should be explainable.
- Decentralized storage does not automatically decentralize authority.
- Privacy also depends on metadata, network, issuer, timing, and correlation protections.
- Regulated and public-sector applications require appropriate legal and institutional governance.

## 10. Platform equation
NODE CORE OS = CORE INFRASTRUCTURE + TRUST PROTOCOLS + APPLICATION RUNTIME
NC-* APPLICATION = CORE CAPABILITIES + TRUST PROTOCOLS + DOMAIN LOGIC + POLICY + GOVERNANCE
TRUST LAYER = IDENTITY + EVIDENCE + REQUIREMENT + SELECTIVE MEMORY + CORROBORATION + PROOF + POLICY
FORGOTTEN → CURRENT REQUIREMENT → REMEMBER ONLY WHAT IS NECESSARY → EVIDENCE → PROOF / DECISION → CONTEXT RELEASE → FORGOTTEN

## 11. Catalog status
This is a master architectural catalog, not a list of production certifications.
Future applications should progress through: PROPOSED → SPECIFIED → PROTOTYPED → TESTED → AUDITED → DEPLOYED.
Only the appropriate status should be claimed for each application.