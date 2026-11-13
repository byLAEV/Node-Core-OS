# Catalog of Products and Services as Business Models for the Node Core OS Identity Node Network by LAEV

**Project:** Node Core OS byLAEV  
**Catalog version:** 1.0.0-draft  
**Catalog status:** Product definitions and business framework in development  
**Economic distribution:** Pending business-model consensus  
**Certificate format:** Project-defined Node Core OS JWS/Ed25519 profile; not X.509 and not an independent accreditation

**Implementation status distinction:** the eight profile identifiers are recognized by the certificate implementation; the eight commercial assessment services remain proposed definitions. The presence of an identifier, specification, test file, or successful certificate-envelope test does not establish that the corresponding security controls are implemented or effective. See [Implementation Status and Evidence Policy](../../docs/IMPLEMENTATION-STATUS-POLICY.md).

## Executive overview

This catalog defines potential security and identity products for organizations that operate websites, Web2 services, enterprise systems, institutional platforms, APIs, and network infrastructure. The products are designed around the Node Core OS identity-node network: individual technical identities and authorized participating nodes may contribute to assessment, verification, monitoring, and delivery of services.

The commercial proposition is to combine **identifiable service providers, documented procedures, verifiable evidence, independent checks, and traceable service delivery**. A certificate records a defined assessment and its claims; it is not proof that a system is invulnerable or that every participating node is trustworthy.

## Business purpose

The network may provide services to customers who need to assess, improve, and monitor digital systems. Participants may act as service providers, evidence producers, independent verifiers, coordinators, or customers. A technical identity attributes work to a key or node; it does not automatically prove civil identity, uniqueness, independence, competence, or honesty.

## Commercial principles

1. Pay for work performed and accepted, not registration or node count.
2. Define scope, eligibility, evidence, acceptance criteria, limitations, and dispute process before pricing.
3. Keep technical verification separate from payment policy.
4. Attribute individual and collective contributions.
5. Separate provider, verifier, and customer-approval roles where practical.
6. Perform offensive security testing only with explicit written authorization.
7. Make claims proportionate to evidence.
8. Protect customer data, personal data, and private keys.
9. Do not invent prices, fees, reward formulas, or allocation percentages.
10. Participation does not guarantee demand, work, approval, or revenue.

## Security products

| # | Product | Profile identifier |
|---:|---|---|
| 1 | Sybil and Fake-Node Resistance Assessment | `sybil-resistance` |
| 2 | P2P Network Partition and Eclipse Resistance Assessment | `p2p-partition-eclipse-resistance` |
| 3 | Byzantine Fault and Node-Collusion Resistance Assessment | `byzantine-collusion-resistance` |
| 4 | Identity Authenticity and Key-Protection Assessment | `identity-key-protection` |
| 5 | Software Supply-Chain and Update Integrity Assessment | `software-supply-chain-integrity` |
| 6 | Availability and DDoS-Resilience Assessment | `availability-ddos-resistance` |
| 7 | IPFS Content-Integrity and Malicious-Content Controls Assessment | `ipfs-content-integrity` |
| 8 | Privilege-Control and Enterprise-Pool Isolation Assessment | `privilege-and-pool-isolation` |

## Additional certificate and service proposals

- [BICDN conflict declaration and resolution certificate](./Certificates/09-bitcoin-conflict-declaration-and-resolution/README.md) — application-level proposal, separate from node identity.
- [NODE-PKI-GUARD](./Certificates/10-node-pki-guard/README.md) — complementary X.509/PKI authorization proposal.
- [HUC Certificates](./Certificates/HUC%20Certificates/README.md) — HUC Direct SDK workspace.
- [Trilema Records — music identity and streaming certificate](./Certificates/certificado-de-streaming-musica-audio-video-trilema-records/README.md) — proposed artistic identity, catalog, audio/video streaming, and distribution service with a local interface planned at `http://127.0.0.1:8765`.

## Implementation and evidence

The eight profile identifiers exist in the certificate implementation, but that does not establish that each corresponding security control is effective. The catalog's test matrix and traceability documents distinguish envelope validation from product-specific efficacy testing.

- [Certificate test and evidence matrix](./CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)
- [Audit and CI index](./AUDIT-AND-CI-INDEX.md)
- [Business model and consensus](./BUSINESS-MODEL-AND-CONSENSUS.md)
- [Certificate implementation](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/security/node_identity_certificate.py)
- [Certificate tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_node_identity_certificate.py)

## Trust and limitations

A signed claim proves that a configured key signed particular content; it does not independently prove that the claim is true. Issuer governance, scope, competent review, evidence quality, key lifecycle, and revocation all matter. This catalog is a project framework under development, not a globally recognized certification scheme or a guarantee against attacks.

## Roadmap

1. Approve product definitions and scope.
2. Map claims to code, tests, and evidence.
3. Add reproducible product-specific tests.
4. Define issuer governance, key lifecycle, and revocation.
5. Define work-order and evidence lifecycle before payment code.
6. Submit economics to the designated consensus process.
7. Conduct independent review and controlled pilots before production claims.

