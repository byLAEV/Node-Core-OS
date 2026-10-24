# Local Mesh Propagation and State Reconciliation

## Scope

Verify multi-node message propagation and state convergence independently from direct-link checks and Kubo content retrieval.

## Three-node propagation test

1. Start isolated nodes A, B, and C with independent data directories and identities.
2. Establish only A-to-B and B-to-C connectivity for the target test; prove A cannot directly reach C.
3. Publish a unique, nonce-bearing message on A.
4. Verify B receives and validates it, then forwards it.
5. Verify C receives the same message and validates its origin, nonce, and payload digest.
6. Save per-node event evidence and topology observations.

A three-node test is invalid if A can directly reach C during the measured scenario.

## State convergence

If a state-root algorithm is implemented, each node must independently calculate the root from canonical state. Compare roots only after the protocol's convergence deadline. Record the canonicalization and hash algorithm. A matching arbitrary string is not proof of a Merkle root.

## Sybil limitation

A single public key presented under multiple IP addresses remains one cryptographic identity. Reject duplicate identities where uniqueness is required; IP diversity is not a substitute for identity diversity. This alone does not solve Sybil resistance.

## Status and rejection

Reject invalid signatures, duplicate/replayed message IDs, divergent roots after the deadline, missing C receipt, unexpected direct A-to-C connectivity, or UID 0. Missing instrumentation is INCOMPLETE, not PASS.

## Implementation boundary

Do not claim GossipSub, CRDT convergence, epidemic broadcast, or consensus unless the actual runtime implements and tests that mechanism. The existing P2P contracts workflow is not automatically evidence for this separate domain.
