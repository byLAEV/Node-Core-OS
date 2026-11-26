# NODE-PKI-GUARD Dual-Model Architecture

## Document control

- Project: NODE Core OS byLAEV
- System: NODE-PKI-GUARD
- Architecture revision: 1.2
- Sequence: LCCP 20
- Status: Architecture specification for implementation and validation
- Language: English
- Shared implementation baseline: NODE-PKI-GUARD v1.0 protocol formats and v1.1 adapters

## 1. Architecture decision

NODE-PKI-GUARD SHALL use one shared security core and two storage/authorization adapters:

1. \`node-pki-guard-standalone\`: a local SQLite implementation for a single administrative trust domain and a single authoritative database.
2. \`node-pki-guard-net\`: an adapter to the authoritative NODE Core OS ledger and its distributed consensus/finality interfaces.

The two editions MUST use the same binding format, authorization format, operation-hash profile, signature suites, policy semantics, and receipt format. They MUST NOT maintain separate cryptographic protocol implementations.

The standalone adapter is not a distributed consensus system. The network adapter MUST NOT emulate consensus with a local SQLite database or process-local lock.

## 2. Shared Core

The shared core owns protocol and security decisions that do not depend on persistence:

- X.509 validation interface and validated-certificate result.
- NODE-PKI-BINDING parsing, schema validation, and issuer-signature verification.
- NODE-PKI-AUTH-UTXO parsing and schema validation.
- Dual Proof-of-Possession verification.
- Domain-separated operation and context hashing.
- Canonical outpoint parsing and normalization.
- STANDARD / PROTECTED / DENY policy evaluation.
- Receipt structure and signature verification.
- Typed interfaces for replay protection, authorization lookup, atomic spend, and finality verification.

Existing implementation modules remain the initial source of truth:

- \`node_core/security/node_pki_guard.py\`
- \`node_core/security/node_pki_guard_x509.py\`

The first modularization step SHOULD extract stable interfaces without duplicating or moving code unnecessarily. A future package layout may expose \`node_pki_guard.core\`, \`node_pki_guard.standalone\`, and \`node_pki_guard.network\`; package renaming is not required for the first functional implementation.

### 2.1 Shared security invariants

- An invalid X.509 certificate MUST never be made valid by a NODE binding or UTXO.
- The X.509 public key used for PoP MUST be extracted from the independently validated certificate.
- Both PoP signatures MUST cover the same domain-separated, canonical challenge bytes.
- A PROTECTED decision is a precondition only. It is not permission to execute an external side effect.
- A protected external operation MUST execute only after the selected adapter confirms the authorization spend according to that adapter's documented commit/finality contract.
- A spent authorization MUST never be restored automatically after an external executor failure.
- A retry with the same idempotency key and same request digest MUST return or reconcile the original result. The same key with different request content MUST be rejected.
- The system MUST distinguish local ACID commit from distributed consensus finality in API types, receipts, logs, and documentation.

## 3. Model A: Standalone SQLite

### 3.1 Intended deployment

Standalone targets local services, single-host deployments, development environments, and enterprise applications that do not require independent validator consensus.

Software licensing and pricing are product/business decisions, not protocol properties. The implementation may be distributed as open-source software; no network fee is charged by this local adapter. Third-party hosting, support, and infrastructure may still have costs.

### 3.2 Transaction and concurrency model

- SQLite 3 is the authoritative local state store.
- Enable Write-Ahead Logging (WAL) and configure a documented durability policy (including \`synchronous\`).
- Start spend transactions with \`BEGIN IMMEDIATE\` so the writer reservation is acquired before checking and changing the outpoint.
- Enforce uniqueness and state transitions with SQL constraints and conditional updates.
- Keep the outpoint availability check, spend transition, and idempotency record in one database transaction.
- Use a busy timeout and bounded retry policy for transient lock contention.
- Do not use \`EXCLUSIVE\` as a routine substitute for correct transaction design.
- A local database protects only operations coordinated through that same database. Multiple independent SQLite files do not share a global double-spend guarantee.

### 3.3 Minimum relational model

The following is a logical baseline. Production migrations MUST add schema versioning, strict types, foreign keys, and appropriate indexes.

\`\`\`sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;

CREATE TABLE IF NOT EXISTS utxo_ledger (
    outpoint TEXT PRIMARY KEY,
    owner_pubkey TEXT NOT NULL,
    authorization_id TEXT NOT NULL UNIQUE,
    binding_id TEXT NOT NULL,
    operation_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('UNSPENT', 'SPENT')),
    created_at TEXT NOT NULL,
    spent_at TEXT,
    operation_id TEXT,
    spend_txid TEXT,
    CHECK (
        (status = 'UNSPENT' AND spent_at IS NULL AND operation_id IS NULL)
        OR
        (status = 'SPENT' AND spent_at IS NOT NULL AND operation_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS idempotency_records (
    operation_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    receipt_json TEXT,
    receipt_hash TEXT,
    state TEXT NOT NULL CHECK (
        state IN ('ACCEPTED', 'SPENT', 'EXECUTING', 'COMMITTED', 'FAILED_REQUIRES_REVIEW')
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (operation_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_utxo_ledger_status
    ON utxo_ledger(status);

CREATE INDEX IF NOT EXISTS idx_idempotency_request_hash
    ON idempotency_records(request_hash);
\`\`\`

The schema is illustrative and MUST be implemented through versioned migrations. The request hash MUST be checked whenever an idempotency record is reused. A uniqueness constraint alone does not prove that a retry has identical content.

### 3.4 Atomic spend algorithm

Within one \`BEGIN IMMEDIATE\` transaction:

1. Look up \`(operation_id, idempotency_key)\`.
2. If found, compare its stored request hash. Reject a mismatch; otherwise return/reconcile its existing state.
3. Load the outpoint and verify it is \`UNSPENT\`, correctly owned, and bound to the requested authorization and operation hash.
4. Apply a conditional update: \`UPDATE ... SET status='SPENT' ... WHERE outpoint=? AND status='UNSPENT'\`.
5. Require exactly one affected row.
6. Insert the idempotency record and request digest.
7. Commit.
8. Only after commit, invoke the external executor through an idempotent execution boundary.
9. Persist the receipt and terminal/reconciliation state.

If the process crashes after the spend commit, the authorization remains spent. Recovery MUST resume or reconcile the same operation; it MUST NOT recreate the authorization.

### 3.5 Standalone finality semantics

Standalone success means a durable local database commit under the configured SQLite durability settings. It MUST be represented as local commit, not as a consensus finality proof. Receipts MUST identify the adapter as \`standalone-sqlite\` and include the local ledger/database instance identifier and commit reference.

## 4. Model B: NODE Core OS Network

### 4.1 Intended deployment

The network adapter targets a future or existing NODE Core OS validator network with an authoritative native ledger, deterministic transaction validation, global UTXO state, and a documented finality mechanism.

The adapter MUST use the real NODE Core OS ledger interfaces. It MUST NOT claim distributed guarantees until the ledger, consensus, finality, reorganization, and multi-node recovery behavior are implemented and tested.

### 4.2 Required ledger capabilities

The network backend contract MUST provide:

- Authoritative UTXO lookup by outpoint.
- Deterministic transaction validation.
- Atomic outpoint consumption within ledger state transition.
- Rejection of concurrent conflicting spends.
- Durable network-wide idempotency keyed by a request digest.
- Policy and epoch validation against consensus state.
- Transaction submission and status lookup.
- Finality proof retrieval and independent proof verification.
- Defined handling for rejected transactions, timeouts, reorganizations, and node recovery.
- A receipt/event reference that can be independently resolved against the ledger.

A local cache may accelerate reads but MUST NOT become the source of truth for spend availability or finality.

### 4.3 Network transaction lifecycle

1. Client constructs a canonical spend request containing the authorization outpoint, operation digest, binding, policy version, proof references, and fee data.
2. Client submits the transaction to the network adapter.
3. Validators independently validate authorization, signatures, policy, validity epoch, and outpoint availability.
4. Consensus accepts one valid spend and rejects conflicting spends.
5. The transaction reaches the network's documented finality threshold.
6. The adapter obtains and verifies the finality proof.
7. The protected external executor runs idempotently.
8. The signed execution receipt is persisted and linked to the finalized ledger transaction.

The executor MUST NOT run merely because a transaction was broadcast or included in a non-final block. If the consensus model has probabilistic finality, the required confirmation threshold and residual reorganization risk MUST be documented.

### 4.4 Fees

The protocol may support fees, but fee economics are not part of the cryptographic validity of a NODE-PKI-GUARD authorization.

The proposed fee expression is:

\`Fee = GasBase + PayloadSize * Multiplier\`

Before production use, the network specification MUST define:

- Fee denomination and integer units.
- Deterministic payload-size measurement.
- Minimum and maximum fee.
- Fee rounding rules.
- Fee payer and authorization.
- Validator/treasury distribution.
- Failed and rejected transaction fee behavior.
- Fee schedule versioning and anti-spam controls.

A finality proof issuer MUST NOT be allowed to award itself a fee by unilateral assertion. Fee allocation MUST be a deterministic ledger state transition validated by consensus. Whether fees go to the block proposer, a validator set, or a consensus treasury is a network governance decision.

## 5. Adapter interface

The shared core SHOULD depend on narrow protocols rather than SQLite or network-specific classes.

Suggested interfaces:

- \`AuthorizationStore.get_authorization(outpoint)\`
- \`AuthorizationStore.consume_authorization(request)\`
- \`IdempotencyStore.get(operation_id, idempotency_key)\`
- \`IdempotencyStore.put_if_absent(request_hash, record)\`
- \`FinalityProvider.wait_for_finality(transaction_id, timeout)\`
- \`FinalityProvider.verify(proof, transaction_id)\`
- \`ReceiptStore.save(receipt)\`

Standalone implements these interfaces with one SQLite transaction and local commit metadata. Network implements them through NODE Core OS ledger transactions, consensus status, and verifiable finality proofs.

The adapter result MUST use explicit status types such as \`LOCAL_COMMITTED\` and \`NETWORK_FINALIZED\`; do not collapse both into a generic \`FINALIZED\` label.

## 6. Receipts

Every receipt MUST include:

- Protocol and receipt format version.
- Adapter type (\`standalone-sqlite\` or \`node-core-os-network\`).
- Operation ID and idempotency key digest.
- Authorization ID and outpoint.
- Binding ID and certificate/SPKI fingerprints.
- Operation and context hashes.
- Execution result hash and executor identity.
- Receipt creation time.
- Adapter commit reference or network transaction/block reference.
- Finality evidence reference when applicable.
- Issuer key ID and receipt signature.

A standalone receipt MUST NOT claim validator quorum or consensus finality. A network receipt MUST include enough data for an independent verifier to validate its ledger inclusion and finality evidence.

## 7. Conformance and test plan

### Shared Core

- Schema positive and negative vectors.
- Binding issuer signature verification and key rotation.
- Dual PoP valid, invalid, wrong-key, wrong-audience, wrong-purpose, and expired challenge cases.
- Challenge replay and nonce uniqueness.
- Operation hash canonicalization and cross-language test vectors.
- STANDARD / PROTECTED / DENY policy matrix.
- X.509 chain, hostname/IP, purpose, validity, and revocation tests.

### Standalone

- Atomic spend under concurrent threads and independent processes sharing one database file.
- Exactly one successful spend for a shared outpoint.
- Duplicate idempotency request returns the original result.
- Same idempotency key with changed request hash is rejected.
- Crash/restart recovery after spend commit and before external execution.
- SQLite WAL recovery and configured durability tests.
- Corrupt database and migration rollback tests.
- Receipt signature and audit trail verification.

### Network

- Two or more independent validator nodes.
- Concurrent conflicting spend submission.
- Deterministic rejection of double spend.
- Finality proof verification by a separate observer.
- Network partition and recovery.
- Reorganization or fork handling according to the consensus model.
- Duplicate transaction and idempotency reconciliation.
- Fee calculation and fee distribution determinism.
- Validator restart and ledger resynchronization.
- End-to-end external execution only after finality.

Mock backends may test adapter orchestration but MUST NOT count as evidence of distributed consensus.

## 8. Implementation order

1. Freeze shared data formats, operation hash, receipt profile, and adapter interfaces.
2. Add SQLite migrations and standalone adapter.
3. Implement standalone atomic spend and persistent idempotency.
4. Run multi-process and crash-recovery tests.
5. Integrate the existing NODE Core OS ledger through the network adapter.
6. Implement consensus-backed atomic spend and finality proof verification.
7. Add deterministic fee calculation and settlement only after network economics are specified.
8. Run multi-node adversarial tests.
9. Publish separate conformance reports for Standalone and Network.

## 9. Current implementation status

At the time this architecture revision is written:

- Shared cryptographic and policy code exists in the repository.
- OpenSSL X.509 adapter exists.
- A UTXO backend protocol/orchestration boundary exists.
- The production SQLite standalone adapter is NOT implemented by this document.
- The production NODE Core OS network adapter is NOT implemented by this document.
- No distributed consensus or multi-node finality guarantee is claimed.
- The fee formula and distribution remain proposals until specified and implemented by the network.

This document is an architecture specification, not proof of implementation, audit, or production readiness.
