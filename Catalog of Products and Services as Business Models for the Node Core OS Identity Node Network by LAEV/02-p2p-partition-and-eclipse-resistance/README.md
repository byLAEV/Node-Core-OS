# P2P Network Partition and Eclipse Resistance Assessment

**Product ID:** `CERT-02`  
**Certificate profile:** `p2p-partition-eclipse-resistance`  
**Catalog status:** Proposed service definition  
**Economic policy:** `pending-consensus`

## What this product does

Assess peer discovery, connectivity diversity, isolation detection, and recovery behavior under controlled, explicitly authorized network scenarios.

This product is intended for authorized enterprise and institutional customers that need evidence-based security assessment of websites, Web2 applications, APIs, network infrastructure, or supporting services. Participating Node Core OS identities may execute approved work, submit evidence, and—where the service contract requires it—contribute to a jointly reviewed result.

## Business value

The service is designed to give a customer a documented view of a defined security question, including test scope, observations, evidence, limitations, and recommended corrective actions. It can support procurement, internal risk management, engineering decisions, or follow-up testing. It is not an automatic guarantee that a customer is secure.

## Threats and assessment objectives

- A node's view of the network is isolated or manipulated.
- Peer discovery returns a biased set of peers controlled by one adversary.
- A partition leaves nodes with stale or conflicting views and no safe recovery path.

## Scope at a glance

- Use a lab or authorized staging network to introduce bounded peer loss and partitions.
- Inspect peer selection, diversity, timeouts, resynchronization, and recovery behavior where implemented.
- Record behavior during and after controlled isolation.

## Expected deliverables

- Network topology and test conditions.
- Partition and peer-isolation timelines.
- Recovery measurements and known failure modes.
- Reproducible configuration and evidence references.

## Acceptance principles

- Only approved test nodes and networks are used.
- The test defines expected safety and recovery criteria in advance.
- Results include failed cases and uncertainty, not only successful paths.
- No claim is made about networks or topologies that were not tested.

## Current implementation and testing status

The profile identifier is accepted by the certificate implementation. Existing P2P/TLS transport tests cover their explicitly tested transport cases; they do not establish full resistance to eclipse attacks or arbitrary partitions.

The `p2p-partition-eclipse-resistance` profile is defined in the project certificate implementation. A certificate profile identifier means the certificate format can name that assessment category; it does not by itself prove that all assessment methods described here are implemented or effective.

See:
- [Service specification](./SERVICE-SPECIFICATION.md)
- [Evidence and testing guide](./EVIDENCE-AND-TESTING.md)
- [Catalog-wide test matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)
- [Certificate implementation](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/security/node_identity_certificate.py)

## Commercial status

This is a proposed service definition. Price, provider remuneration, verifier remuneration, fees, and allocation of revenue are **not defined**. They must be decided by the business-model consensus process. No revenue or customer demand is guaranteed.

## Important limitation

A certificate records defined claims made under an issuer and verification policy. A valid signature establishes integrity and key-based origin of the signed claims; it does not prove every claim is true. The final report must state the exact system, version, period, methods, results, exclusions, and known limitations.
