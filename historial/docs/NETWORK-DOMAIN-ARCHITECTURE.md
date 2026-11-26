# Node Core OS byLAEV — Independent Network Domains

## Purpose

Node Core OS verifies three network domains independently. Evidence from one domain MUST NOT be used as proof that another domain works.

1. **Local P2P link** — direct authenticated node-to-node transport.
2. **Local decentralized mesh** — multi-node message propagation and deterministic state reconciliation.
3. **IPFS / Kubo** — content-addressed retrieval, integrity verification, and signed receipt.

## Architectural boundaries

- Native P2P status and Kubo swarm status are separate observations.
- Discovery is not authentication; authentication is not consensus.
- A configured bootstrap address is not proof of an active connection.
- A successful Kubo retrieval does not prove native P2P connectivity.
- A signed receipt proves possession of a signing key, not a real-world identity unless the public key is independently bound to the expected node.
- Do not claim Noise XX/IK, GossipSub, CRDT, or Merkle consensus unless the implementation and tests actually exercise them.

## Evidence states

- `PASS`: the test ran, all required assertions passed, and evidence was validated.
- `FAIL`: the test ran and a required assertion failed.
- `SKIPPED`: the test did not run. It is never a pass.
- `INCOMPLETE`: execution occurred but required evidence is missing or unverifiable.

## Non-root requirement

All local and CI test commands must execute as an ordinary user. A test must fail closed if its effective UID is zero. Do not use `sudo`, `su`, or privilege escalation.

## Current implementation boundary

The repository has existing native P2P services, network status reporting, Kubo integration, and the Termux remote Kubo read workflow. The exact status of any proposed test helper must be established from the checked-out branch; this architecture document does not assert that a future helper or protocol is already implemented.
