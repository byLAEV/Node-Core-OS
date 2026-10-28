# Catalog of Products and Services as Business Models for the Node Core OS Identity Node Network by LAEV

**Project:** Node Core OS byLAEV  
**Catalog version:** 1.0.0-draft  
**Catalog status:** Product definitions and business framework in development  
**Economic distribution:** Pending business-model consensus  
**Certificate format:** Project-defined Node Core OS JWS/Ed25519 profile; not X.509 and not an independent accreditation

**Implementation status distinction:** the eight profile identifiers are recognized by the certificate implementation; the eight commercial assessment services remain proposed definitions. The presence of an identifier, specification, test file, or successful certificate-envelope test does not establish that the corresponding security controls are implemented or effective. See [Implementation Status and Evidence Policy](../../docs/IMPLEMENTATION-STATUS-POLICY.md).

## Executive overview

This catalog defines eight potential security products for organizations that operate websites, Web2 services, enterprise systems, institutional platforms, APIs, and network infrastructure. The products are designed around the Node Core OS identity-node network: individual technical identities and authorized participating nodes may contribute to the assessment, verification, monitoring, and delivery of security services to enterprise or institutional customers.

The commercial proposition is to combine **identifiable service providers, documented procedures, verifiable evidence, independent checks, and traceable service delivery**. A certificate is the record of a defined assessment and its claims; it is not, by itself, proof that a system is invulnerable or that every node participating in the network is trustworthy.

The eight certificate profiles already exist in the Node Core OS certificate implementation as recognized profile identifiers. The repository also contains automated tests and GitHub Actions workflows for certificate handling and related security components. However, the existence of a profile identifier or a passing test of the certificate format does **not** establish that every corresponding security control has been fully implemented, tested against realistic attacks, independently audited, or approved for production. This catalog makes those distinctions explicit.

## Business purpose

The network may provide security products and services to customers who need to assess, improve, and monitor the resilience of digital services. Depending on authorization and service scope, participating identities and nodes may contribute as:

- **Service providers** — execute an assigned assessment, monitoring task, verification, or other contracted work.
- **Evidence producers** — generate logs, test results, signed reports, hashes, measurements, and reproducible artifacts.
- **Independent verifiers** — check whether submitted evidence meets published acceptance criteria, subject to conflict-of-interest rules.
- **Coordinators** — organize authorized work across multiple participating nodes and track completion.
- **Enterprise or institutional customers** — define scope, provide authorization, review accepted deliverables, and pay for contracted services.

A personal or technical identity can help attribute work to a key or node. It does not automatically prove a person's civil identity, uniqueness, independence, competence, or honesty. Organizational identity and authority must be verified separately where the service requires them.

## Commercial principles

1. **Pay for work performed and accepted.** Registration, node count, identity count, or a certificate purchase alone must not automatically generate rewards.
2. **Define the service before pricing it.** Each product needs a scope, eligibility rules, task definition, evidence requirements, acceptance criteria, limitations, and dispute process.
3. **Keep technical verification separate from payment policy.** The catalog describes services; the network's business-model consensus will determine pricing and distribution rules.
4. **Recognize individual and collective work.** Where a service requires multiple nodes, each contribution and the combined deliverable should be traceable.
5. **Prevent self-certification abuse.** Where practical, the provider, verifier, and customer approver should be separate roles, with conflicts of interest disclosed.
6. **Use authorized testing only.** Any offensive security testing must have explicit written authorization and defined targets, methods, time windows, and safety limits.
7. **Make claims proportionate to evidence.** Certificates describe scope, version, date, results, limitations, issuer, and revocation status. They do not promise absolute security.
8. **Protect customer data.** Do not publish secrets, private keys, personal data, or sensitive vulnerability details in public evidence records.
9. **Do not invent economics.** Prices, fees, reward formulas, reserves, and allocation percentages remain undefined until approved through the business-model consensus process.
10. **No income guarantee.** Participation does not guarantee customer demand, work allocation, certificate approval, or revenue.

## The eight security products

| # | Product | Profile identifier | Commercial purpose |
|---:|---|---|---|
| 1 | Sybil and Fake-Node Resistance Assessment | `sybil-resistance` | Assess controls against fabricated or duplicated network identities and misleading participation claims. |
| 2 | P2P Network Partition and Eclipse Resistance Assessment | `p2p-partition-eclipse-resistance` | Assess peer-discovery, connectivity, and recovery behavior under authorized network-isolation scenarios. |
| 3 | Byzantine Fault and Node-Collusion Resistance Assessment | `byzantine-collusion-resistance` | Assess protocol behavior when participants are faulty, inconsistent, or colluding within a defined threat model. |
| 4 | Identity Authenticity and Key-Protection Assessment | `identity-key-protection` | Assess identity binding, signature verification, key handling, and impersonation controls. |
| 5 | Software Supply-Chain and Update Integrity Assessment | `software-supply-chain-integrity` | Assess artifact provenance, dependency controls, signatures, and update verification. |
| 6 | Availability and DDoS-Resilience Assessment | `availability-ddos-resistance` | Assess authorized availability, resource limits, rate controls, and recovery under defined load scenarios. |
| 7 | IPFS Content-Integrity and Malicious-Content Controls Assessment | `ipfs-content-integrity` | Assess content addressing, retrieval integrity, and controls for handling potentially malicious content. |
| 8 | Privilege-Control and Enterprise-Pool Isolation Assessment | `privilege-and-pool-isolation` | Assess access boundaries, least privilege, and separation between organizational or service pools. |

Each product has its own folder with a customer-facing overview, a service specification, and an evidence/testing guide.

## Catalog sections

- [Certificates — eight individual certificate products](./Certificates/README.md)
- [Cybercrime (Information Security) — decentralized technology and IPFS](./Cybercrime/README.md)

## Product directory

1. [Sybil and Fake-Node Resistance](./Certificates/01-sybil-and-fake-node-resistance/README.md)
2. [P2P Partition and Eclipse Resistance](./02-p2p-partition-eclipse-resistance/README.md)
3. [Byzantine Fault and Collusion Resistance](./Certificates/03-byzantine-fault-and-collusion-resistance/README.md)
4. [Identity Authenticity and Key Protection](./Certificates/04-identity-authenticity-and-key-protection/README.md)
5. [Software Supply-Chain Integrity](./Certificates/05-software-supply-chain-integrity/README.md)
6. [Availability and DDoS Resilience](./Certificates/06-availability-and-ddos-resilience/README.md)
7. [IPFS Content Integrity](./Certificates/07-ipfs-content-integrity/README.md)
8. [Privilege Control and Pool Isolation](./Certificates/08-privilege-control-and-pool-isolation/README.md)

Shared governance and verification documents:

- [Business model and economic consensus](./BUSINESS-MODEL-AND-CONSENSUS.md)
- [Certificate test and evidence matrix](./CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)

## Certificate implementation and automated testing

The current certificate implementation is located at:
- [Node identity certificate implementation](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/security/node_identity_certificate.py)
- [Certificate unit tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_node_identity_certificate.py)
- [Certificate claims JSON Schema](https://github.com/byLAEV/Node-Core-OS/blob/main/schemas/node-core-node-identity-certificate.schema.json)
- [Certificate format specification](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/NODE-IDENTITY-CERTIFICATE-FORMAT.md)
- [Node Identity Certificate Conformance workflow](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/node-identity-certificate.yml)
- [Certificate adversarial tests workflow](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/certificate-adversarial-tests.yml)
- [Existing security test report and CI references](https://github.com/byLAEV/Node-Core-OS/blob/main/docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.md)

The conformance test suite covers certificate-format behavior such as valid issuance and verification, tampering rejection, unknown issuers, revocation handling, expiry, maximum lifetime, and unsupported profiles. Related adversarial workflows test other, specifically named components. These results must not be represented as dedicated efficacy tests for all eight product profiles. See the [test and evidence matrix](./CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md) for the known distinction between existing test coverage and future work.

## Certificate status and customer trust

A customer-facing certificate record should identify, at minimum:

- certificate ID and profile;
- issuer and key identifier;
- subject node or assessed asset;
- assessment scope and version;
- issue and expiry timestamps;
- evidence references and their integrity hashes;
- test methods and results;
- limitations and exclusions;
- verification instructions and revocation status.

The signing key establishes the origin and integrity of a signed claim under the configured trust policy. It does not independently prove that the claim is true. Trust also depends on issuer governance, scope, competent assessment, evidence quality, revocation distribution, and independent review.

## Business model status

**Economic policy: `pending-consensus`.** No service prices, provider percentages, commissions, token rewards, or distribution formulas are set by this catalog.

The business-model consensus process must define eligible participants, work units, evidence acceptance, independent verification, contribution attribution, service valuation, cost handling, dispute resolution, payment settlement, anti-fraud controls, governance, and legal compliance. Until that process is approved and implemented, this directory is a product and service specification—not a live marketplace or promise of payment.

## Roadmap

1. Review and approve the product definitions and their scope.
2. Map each product's claims to concrete code, tests, and evidence.
3. Add dedicated, safe, reproducible tests for each profile and integration point.
4. Define issuer governance, key lifecycle, and reliable revocation distribution.
5. Design the work-order and evidence lifecycle before payment code.
6. Submit the economic model to the designated consensus process.
7. Conduct independent security review and controlled pilot trials before production claims.

## Disclaimer

This catalog describes a project-defined security service framework under development. It is not a globally recognized certification scheme, does not replace standard TLS/X.509 validation, and does not guarantee protection against every cyberattack. All security findings and certificates must state their scope, evidence, limitations, and review status.


## Audit, test evidence, and CI traceability

- [Eight-certificate audit and GitHub Actions index](./AUDIT-AND-CI-INDEX.md)
- [Certificate test and evidence matrix](./CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)

Every product folder includes `TEST-TRACEABILITY.md` to map its profile to related tests, workflows, evidence boundaries, and missing product-specific tests. The catalog-integrity workflow validates directory/profile consistency and certificate-envelope tests; it does not claim that all eight attack classes have been defeated.
