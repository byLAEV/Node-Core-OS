# Node Core OS — Master Technical Audit

- Audit date: 2026-10-29
- Repository: `byLAEV/Node-Core-OS`
- Base branch: `main`
- Audited base commit: `8d44a25a6a3dee3b833799bc2f1799c0878edd85`
- Audit branch: `audit/master-technical-audit-2026-10-29`
- Status: `IN_DEVELOPMENT` — initial source inspection; not a release certification.

## 1. Scope and evidence standard

This document records findings from source and workflow inspection at the exact base commit above. It does not claim that the test suite was executed during this audit. A source file, test file, workflow definition, or historical green run is not by itself proof that the current commit passed an operational test.

Each finding must eventually include: exact commit, file path, relevant lines, test command or workflow run, observed result, environment, and limitations.

## 2. Repository architecture observed

The repository contains at least these active architectural areas:

- Core runtime and BIOS: `node_core/runtime.py`, `node_core/ui.py`, `node_core/config.py`.
- Local persistence and content: `node_core/storage.py`, `node_core/content.py`, `node_core/evidence.py`, `node_core/external_cids.py`.
- Kubo/IPFS lifecycle: `node_core/ipfs.py`.
- Kubo network operations: `node_core/network.py`.
- Technical node identity: `node_core/identity/node_identity.py`.
- Declared profile and node association: `node_core/identity/profile.py`, `node_core/identity/associations.py`.
- Native P2P: `node_core/p2p/` including authentication, TLS transport, discovery, trust store, sessions and secure messaging.
- Applications: `applications/hashpaper/`, `applications/p2p_contracts/`, and `applications/eulora2-transponder/`.
- Installer and updater: `installer/`.
- Tests: `tests/`, plus application-specific test directories.
- CI: `.github/workflows/`.

This is a broad initial inventory from repository search, not a complete filesystem manifest. Search indexing and result limits mean omitted paths must not be interpreted as absent.

## 3. Confirmed source-level findings

### 3.1 Runtime composition

`node_core/runtime.py` constructs shared instances of configuration, local storage, Kubo manager, network, content manager, evidence manager, identity profile store, identity presence, external CID library and My Life blog. Native P2P cryptography components are loaded lazily.

The runtime's comments and status output explicitly distinguish LAN discovery from worldwide discovery. `native_p2p_status()` reports `discovery_scope: "lan"` and `wan_discovery_running: False`, with an explanatory error stating that WAN discovery requires a configured rendezvous/bootstrap service.

**Assessment:** this is a useful explicit boundary. Do not describe native P2P discovery as global or worldwide based on the current runtime.

### 3.2 Two different identity layers already exist

`node_core/identity/node_identity.py` implements a persistent Ed25519 technical identity. It stores an unencrypted PEM private key, applies restrictive filesystem permissions, validates the public/private key correspondence and node identifier, and fails closed if only one of the identity files exists.

The source docstring explicitly states that filesystem permissions do not protect the private key from a compromised process running as the same user.

`node_core/identity/associations.py` already implements local declared-profile-to-node association using a fresh one-time challenge and Ed25519 signature. It persists associations, consumes valid challenges, and supports revocation records. Its module documentation explicitly limits the proof: it proves control of the node key, not civil identity or ownership of declared profile attributes.

**Assessment:** earlier statements that there was no identity-association implementation would be inaccurate. A profile-to-node association primitive exists. The audit has not established a GitHub OAuth / GitHub User ID binding flow. Genesis Join must reuse or deliberately extend the existing association model rather than duplicate it.

### 3.3 Kubo and content semantics

`node_core/ipfs.py` wraps Kubo CLI and RPC operations. The inspected implementation applies bounded command timeouts and normalizes timeout and OS execution failures into `KuboError`. The Kubo status check probes the local API.

`node_core/content.py` provides a content registry and operations for add, retrieve, pin, unpin, publish and share. The source comments explicitly state that CID publication is not IPNS publication and that identity/key-backed naming belongs to a future identity layer.

**Assessment:** distinguish local registry state, local pin state, CID addressability, network retrieval, and durable availability. They are separate claims and need separate tests.

### 3.4 Native P2P versus Kubo swarm

`node_core/network.py` uses Kubo for Peer ID, connected peers, multiaddress connection and ping. Native P2P has separate authentication, trust and TLS components under `node_core/p2p/`.

The runtime reports that signed discovery announcements do not themselves grant trust or authorize application use. It also distinguishes a signed announcement from a fresh authenticated session.

**Assessment:** maintain this distinction in documentation and status UI. A Kubo swarm peer is not automatically a trusted Node Core application peer.

### 3.5 Existing P2P Contracts Genesis is not GitHub Genesis Join

`applications/p2p_contracts/p2p_contracts/genesis.py` loads and validates the P2P Contracts genesis manifest and calculates deterministic content/propagation hashes. Its module docstring explicitly says these helpers do not implement authenticated acceptance or claim a peer accepted a hash.

The manifest identifies the application as `node-core-os-p2p-contracts` and references the Bitcoin Mainnet genesis block hash.

**Assessment:** this Genesis is application/protocol genesis for P2P Contracts. It is not GitHub account onboarding and must not be conflated with GitHub Genesis Join.

## 4. CI and test posture observed

The inspected `.github/workflows/ci.yml` defines a Linux terminal job on Ubuntu 24.04 with Python 3.12. It runs Python compile validation, installer shell tests, and `python -m unittest discover -s tests -v`.

The same workflow contains experimental multi-node jobs guarded by `if: false`, including a three-Kubo-node integration job and a cross-VM P2P node job. Another inspected workflow section for independent Ubuntu P2P Contracts E2E is also explicitly disabled.

**Assessment:** source-level test definitions exist, but disabled jobs are not executing evidence. The current audit did not execute the test suite or retrieve and validate a successful run for the audited SHA. This report therefore makes no claim that CI is green.

## 5. Initial risk register

| ID | Finding | Severity | Evidence / next verification |
|---|---|---|---|
| AUD-001 | GitHub account association flow not demonstrated in inspected source | High | Search all OAuth, GitHub API, account ID and onboarding paths; inspect installer/UI integration |
| AUD-002 | Existing profile-to-node association must be reused or explicitly extended | High | Review full association API, tests, persistence, challenge expiry and replay behavior |
| AUD-003 | Node private key is unencrypted PEM | High | Threat model, OS keystore options, backup/recovery and same-user compromise analysis |
| AUD-004 | Native WAN discovery is explicitly unavailable in runtime status | High | Deploy/configure rendezvous/bootstrap service and run independent-node tests |
| AUD-005 | Multi-node CI jobs are disabled in inspected workflow | High | Decide reactivation gate; run isolated three-node tests only after prerequisites |
| AUD-006 | CID publication is not IPNS publication and not a durability guarantee | Medium | Verify pinning, remote retrieval, replication and provider persistence separately |
| AUD-007 | Broad repository inventory is incomplete | Medium | Obtain complete recursive tree and paginate all results |
| AUD-008 | Kubo swarm and native trusted-peer semantics can be confused | Medium | Ensure APIs, UI and docs preserve separate states |

Severity is an audit prioritization, not a claim of exploitable vulnerability.

## 6. Required next audit passes

1. Complete recursive repository tree inventory and branch pagination.
2. Inspect installer, updater, configuration, storage and BIOS source with line-level evidence.
3. Inspect all identity modules and tests, including challenge expiration, replay, concurrent writes and revocation.
4. Inspect P2P protocol modules and tests, including transport authentication, message delivery, persistence, retries and revocation.
5. Inspect application packaging and dependency boundaries.
6. Inspect workflow definitions and retrieve run results for the exact audited commit.
7. Execute reproducible tests in an isolated environment; record commands, versions, logs and exit codes.
8. Produce a final finding matrix with `PROPOSED`, `IMPLEMENTED`, `TESTED`, `VERIFIED`, `SECURITY_REVIEWED` and `OPERATIONAL` states according to the repository's implementation-status policy.

## 7. Change policy during audit

- Do not modify `main`.
- Do not delete or merge branches as part of the audit.
- Do not alter user data, local Kubo repositories or production identities.
- Keep audit documentation on this dedicated branch.
- Any code fix must be a separate, scoped change with tests and review.
- Never mark a component `VERIFIED` solely because source or test files exist.

## 8. Current conclusion

Node Core OS already contains substantial implementations for local storage/content, Kubo integration, Ed25519 node identity, declared-profile-to-node association, and native P2P components. The runtime deliberately reports LAN-only native discovery and separates discovery, trust and authenticated sessions.

The immediate architectural opportunity for Genesis is not to invent node identity from scratch. It is to add GitHub account authentication and a verifiable GitHub User ID association to the existing technical node identity and association infrastructure, while preserving the distinction between GitHub account authentication, control of the node key, and real-world identity claims.

**Audit status: initial source inspection only. Full repository audit and runtime verification remain open.**
