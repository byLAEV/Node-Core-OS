# Certificates

This directory contains eight Node Core OS security-assessment certificate products, the separate BICDN conflict-declaration certificate proposal, and the NODE-PKI-GUARD complementary X.509/PKI authorization proposal. The product folders retain their individual specifications, evidence guides, and test traceability documents.

## Certificate products

1. [Sybil and Fake-Node Resistance](./01-sybil-and-fake-node-resistance/README.md) — `sybil-resistance`
2. [P2P Partition and Eclipse Resistance](./02-p2p-partition-and-eclipse-resistance/README.md) — `p2p-partition-eclipse-resistance`
3. [Byzantine Fault and Collusion Resistance](./03-byzantine-fault-and-collusion-resistance/README.md) — `byzantine-collusion-resistance`
4. [Identity Authenticity and Key Protection](./04-identity-authenticity-and-key-protection/README.md) — `identity-key-protection`
5. [Software Supply-Chain Integrity](./05-software-supply-chain-integrity/README.md) — `software-supply-chain-integrity`
6. [Availability and DDoS Resilience](./06-availability-and-ddos-resilience/README.md) — `availability-ddos-resistance`
7. [IPFS Content Integrity](./07-ipfs-content-integrity/README.md) — `ipfs-content-integrity`
8. [Privilege Control and Pool Isolation](./08-privilege-control-and-pool-isolation/README.md) — `privilege-and-pool-isolation`

9. [Bitcoin Conflict Declaration and Resolution Certificate](./09-bitcoin-conflict-declaration-and-resolution/README.md) — `bitcoin-conflict-declaration` (proposed application-level case credential; not a node identity profile)
10. [NODE-PKI-GUARD — Complementary X.509/PKI Authorization](./10-node-pki-guard/README.md) — `NODE-PKI-GUARD` (proposed UTXO-based authorization layer; does not replace X.509 or existing CAs)

11. [HUC Certificates — HUC Direct SDK](./HUC%20Certificates/README.md) — dedicated workspace for HUC credential lifecycle, SDK integrations, API contracts, tests, and release evidence (SDK 0.8.0 artifacts pending repository import and verification)

## Evidence and status

- [Certificate test and evidence matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)
- [Audit and CI index](../AUDIT-AND-CI-INDEX.md)
- [Business model and consensus](../BUSINESS-MODEL-AND-CONSENSUS.md)

**Important:** A recognized certificate profile or passing certificate-envelope test does not prove that the corresponding attack class has been defeated. Each product's claims must remain limited to its actual implementation, tests, and documented evidence. Commercial availability and economic policy remain subject to the catalog's stated status.
