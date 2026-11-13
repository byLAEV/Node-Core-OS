# Certificates

This directory contains Node Core OS security-assessment profiles and additional application/service credential proposals. Each product folder must distinguish documented proposals from implemented and tested functionality.

## Certificate products

1. [Sybil and Fake-Node Resistance](./01-sybil-and-fake-node-resistance/README.md) — `sybil-resistance`
2. [P2P Partition and Eclipse Resistance](./02-p2p-partition-and-eclipse-resistance/README.md) — `p2p-partition-eclipse-resistance`
3. [Byzantine Fault and Collusion Resistance](./03-byzantine-fault-and-collusion-resistance/README.md) — `byzantine-collusion-resistance`
4. [Identity Authenticity and Key Protection](./04-identity-authenticity-and-key-protection/README.md) — `identity-key-protection`
5. [Software Supply-Chain Integrity](./05-software-supply-chain-integrity/README.md) — `software-supply-chain-integrity`
6. [Availability and DDoS Resilience](./06-availability-and-ddos-resilience/README.md) — `availability-ddos-resistance`
7. [IPFS Content Integrity](./07-ipfs-content-integrity/README.md) — `ipfs-content-integrity`
8. [Privilege Control and Pool Isolation](./08-privilege-control-and-pool-isolation/README.md) — `privilege-and-pool-isolation`
9. [Bitcoin Conflict Declaration and Resolution](./09-bitcoin-conflict-declaration-and-resolution/README.md) — application-level proposal
10. [NODE-PKI-GUARD](./10-node-pki-guard/README.md) — complementary X.509/PKI authorization proposal
11. [HUC Certificates](./HUC%20Certificates/README.md) — HUC Direct SDK workspace
12. [Trilema Records — Music Identity and Streaming Certificate](./certificado-de-streaming-musica-audio-video-trilema-records/README.md) — `trilema-music-streaming`

## Evidence and status

- [Certificate test and evidence matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)
- [Audit and CI index](../AUDIT-AND-CI-INDEX.md)
- [Business model and consensus](../BUSINESS-MODEL-AND-CONSENSUS.md)

**Important:** A recognized profile or passing envelope test does not prove that an attack class has been defeated. Likewise, the Trilema Records folder is a service specification and proposed credential schema; it does not mean that the local web interface, media streaming, rights verification, credential issuance, or DSP distribution is implemented or operational.
