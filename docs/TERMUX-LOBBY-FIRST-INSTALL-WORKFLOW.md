# Termux Lobby — First-install identity-gated workflow

**Status:** implementation plan; no Bitcoin-key onboarding is implemented by this document.  
**Target branch:** `feature/termux-local-lobby`  
**Target environment:** native Termux on Android ARM64, unprivileged user.  
**Primary entry point:** `127.0.0.1:8765`  
**Canonical Node Core OS installer:** `bash installer/install.sh`

## 1. Goal

Deliver a first-install flow in the Lobby that:

1. Detects that Node Core OS is not installed and that the Termux environment is eligible.
2. Collects a full name and a Bitcoin private key in raw hexadecimal form through a protected first-install form.
3. Derives the Bitcoin address locally and proves control of the corresponding key without retaining or transmitting the private key.
4. Creates a private, local identity-to-node association using the existing Node Core OS identity model.
5. Enables the first-install action only after all prerequisites and identity checks pass.
6. Downloads and verifies the official installation package, then executes only its canonical `installer/install.sh`.
7. Displays actual installer output and the exit/verification result in a visible Lobby terminal panel.
8. Verifies the installed Node Core OS identity, commits the local identity association, and opens the installed Node Core OS launcher.
9. Displays the associated public Bitcoin address in the Node Core OS main-menu header.
10. Keeps the update path independent: updates do not request a Bitcoin private key and must preserve identity and data.

The button is not a mock action. Completion is reported only after the official installer and post-install identity checks succeed.

## 2. Repository baseline verified

The current Lobby branch is `feature/termux-local-lobby`. It contains the Termux Lobby implementation and is 146 commits ahead of `main`, with `main` as its merge base. Continue the work on this branch unless a later repository inspection establishes a newer approved integration branch.

### Existing Lobby capabilities to reuse

- `compatibility/termux/lobby/server.py`
  - native Termux and Node Core detection;
  - latest stable release metadata validation;
  - verified package staging and SHA-256 receipts;
  - safe archive extraction and canonical installer selection;
  - authenticated local package execution and output polling;
  - an existing interactive PTY implementation for the separately launched Node Core terminal.
- `compatibility/termux/lobby/web/index.html`
  - install and update panels;
  - authenticated local API calls;
  - package execution output display;
  - existing interactive terminal UI.
- `compatibility/termux/tests/test_server.py` and `test_release_metadata.py`
  - Lobby server, transport, local API, release metadata, package digest and extraction tests.
- `.github/workflows/termux-lobby.yml`
  - automated Lobby validation workflow.
- `compatibility/termux/install-lobby.sh`
  - installs the Lobby separately and preserves its persistent service state.

Do not create a second installer, a parallel package downloader, an unrestricted shell endpoint, or a second Lobby service.

### Existing Node Core OS identity capabilities to reuse

- `node_core/identity/node_identity.py`: persistent Ed25519 technical node identity and node ID.
- `node_core/identity/profile.py`: private, local, user-declared personal profile. Its current schema requires full name, issuing country, document type and document number; it must not be silently weakened to accommodate a shorter first-run form.
- `node_core/identity/associations.py`: one-time challenge/signature flow proving control of the Node Core OS Ed25519 node key when associating a profile with a node.
- `node_core/identity/entity_registry.py`: local entity registry supporting a declared person entity, display name and node references without requiring document fields.
- `docs/IDENTITY-DESIGN-PRINCIPLES.md` and `docs/IDENTITY-ENTITY-NODE-MODEL.md`: normative privacy and identity semantics.

The existing Ed25519 association proves control of the technical node key. It does **not** prove control of a Bitcoin key. Bitcoin proof must be a separate, explicit association and must not replace or masquerade as the Ed25519 node identity.

### Existing installer contract to preserve

- `installer/install.sh` is the single canonical Linux/Termux entry point.
- Native Termux uses `pkg` and Android-native Python cryptography/Kubo dependencies.
- Python 3.10+ and `cryptography>=42.0.0` are already part of the core dependency contract.
- Installation and update run as the normal Termux user; root and sudo are rejected.
- The installer initializes the existing Ed25519 NODE ID and verifies the installation.
- The updater preserves user identity, configuration, local storage and Kubo/IPFS data.
- `installer/termux-install.sh` is a compatibility alias, not an alternative implementation.

Do not install Linux manylinux wheels into Termux, add `requests` where standard-library `urllib` is already used, or add dependencies without tracing them to actual imports and executable behavior.

## 3. Important current gaps and release gate

The current `compatibility/termux/README.md` explicitly says that Bitcoin WIF/HEX reference-key derivation is not implemented and that the Lobby does not collect Bitcoin private keys. The existing source confirms that the Lobby's installation runner currently installs the canonical release package without a Bitcoin identity step.

There is also a release-coherence issue to resolve before calling the feature production-ready:

- GitHub currently exposes a published stable `v1.5.6` release with both installer and updater archives and SHA-256 asset digests.
- That release points to source commit `08d994574775a0ec3d9dcc4b2e88862152d1ea3b`.
- The current `main` commit inspected for this plan is `ba2152a51d06666952e831167b5473e71a4c1e61`, 99 commits ahead of that release source.
- The README's release note and the live Releases API do not currently describe the same release state.

Therefore, do not equate “latest stable release metadata is valid” with “the release contains the latest approved source.” Before a production first-install rollout, synchronize release documentation, verify the exact package contents against the approved source commit, and publish a new version from the approved commit using the repository's verified release workflow. Do not silently substitute a development branch archive for a signed/verified release package.

## 4. Identity and Bitcoin cryptography contract

### 4.1 Separate the identity layers

The first-install record must distinguish:

| Data | Meaning | Status |
|---|---|---|
| Full name | User-entered name | `declared` |
| Bitcoin address | Public address derived from the supplied key | `derived` |
| Bitcoin key possession | Successful local proof using a fresh challenge | `control_verified` |
| Node ID | Existing Ed25519 technical node identifier | `cryptographic_node_identity` |
| Entity/profile ID | Random persistent local identifier | `local_identifier` |
| Civil identity/document authenticity | Not checked by first installation | `not_verified` |

A valid Bitcoin key proves control of that cryptographic key at the time of the proof. It does not prove the user's legal name, personhood, document authenticity, exclusive ownership, or trustworthiness. Reusing the same Bitcoin key on two installations must yield the same Bitcoin address but distinct technical Node IDs and distinct local installation/entity IDs.

### 4.2 Private-key handling — mandatory

The raw private key is a secret and must never be written into Node Core OS identity documents.

Required controls:

- Accept only the explicitly documented raw-key format; reject malformed hex, out-of-range scalars, WIF, seed phrases and extended keys unless a later specification explicitly adds them.
- Prefer local browser-side derivation and challenge signing using a pinned, reviewed, offline-bundled cryptographic library. The raw key must not be sent to the Lobby server, GitHub, an external API, IPFS, analytics or any remote endpoint.
- If browser-side signing cannot be implemented and verified, stop and design a native Termux secure prompt. Do not fall back to transmitting the raw key through an untrusted self-signed local HTTPS connection.
- Keep secret material only in short-lived memory; clear the input and mutable byte buffers as soon as the operation ends. Document that JavaScript/runtime zeroization is best-effort, not an absolute memory-erasure guarantee.
- Never put the key in a URL, query string, command-line argument, environment variable, shell command, terminal output, exception, crash report, application log, audit log, localStorage, sessionStorage, cookie, configuration file, temporary file or persisted JSON.
- Do not include the private key in the pending-install record. Only public address/key material, a scoped challenge proof and user-declared display name may be staged.
- Do not send the key to the official installer. The official installer must remain responsible for normal dependencies, Node Core filesystem setup, Ed25519 initialization and verification.

### 4.3 Address format decision

A private scalar does not identify one universal textual Bitcoin address. Network and address script type matter. The implementation must make this explicit and test it.

Proposed first-release default, pending product-owner approval:

- Network: Bitcoin mainnet.
- Key input: 32-byte raw hexadecimal scalar (64 hexadecimal characters).
- Public key: compressed secp256k1 public key for ECDSA address types.
- Address type: native SegWit P2WPKH (`bc1q...`).

Before implementation is considered complete, decide whether the first release must also support legacy P2PKH, nested SegWit P2SH-P2WPKH, testnet/signet, or Taproot P2TR. Never guess an address type from the private scalar. Display the selected network and address type beside the derived address.

### 4.4 Candidate library approach

Evaluate an offline browser bundle using the maintained `@scure/btc-signer` package for supported Bitcoin address/script formats and `@noble/curves` for a domain-separated secp256k1 challenge signature if the required signing API is not already exposed by the selected BTC library.

Candidate documentation:
- https://github.com/paulmillr/scure-btc-signer
- https://jsr.io/@scure/btc-signer
- https://www.npmjs.com/package/@noble/curves

The current package documentation describes browser support and support for P2PKH, P2WPKH, P2SH, P2WSH and Taproot formats. This is a candidate, not an automatic dependency approval. Pin exact versions, include licenses and reproducible bundle instructions, vendor the static browser assets into the repository, and test the exact production bundle. No CDN, dynamic import or internet dependency is permitted at runtime. Do not add Node.js as an end-user Termux requirement merely to build a browser bundle.

The backend can use the already-required Python `cryptography` package to verify a public-key challenge signature, provided the proof encoding and address binding are fully specified and tested. Do not introduce a second Python Bitcoin dependency unless a documented requirement cannot be met by the vendored browser implementation and existing runtime.

### 4.5 Challenge and address binding

- Generate a cryptographically random, single-use nonce on the Lobby server.
- Bind the challenge to the purpose string, current Lobby installation/session, intended entity/profile ID, selected network/address type, expiry and a unique challenge ID.
- Sign the exact documented message bytes using the Bitcoin key in the browser.
- Submit only the derived public address, public key, challenge ID, signature and non-secret identity fields.
- Verify the signature, derive the address again from the submitted public key, compare it with the claimed address, enforce expiry, and consume the challenge exactly once.
- Reject altered, expired, replayed, malformed or address-mismatched proofs.
- Store the successful result as a public-key association record, not as a private-key record.

If a standard Bitcoin message-proof format is selected, document its supported address types and verify interoperability. If a Node Core-specific proof envelope is selected instead, domain-separate it and document its format/version so it cannot be confused with an ordinary Bitcoin transaction signature.

## 5. Proposed persisted identity model

Use the existing private local identity directory and existing node/entity primitives. Do not put personal profile data into the Lobby's read-only diagnostic report or publish it to Kubo/IPFS.

The minimal first-install path should require only:

- full name (declared); and
- a valid Bitcoin proof for the selected address type/network.

Do not require a passport number or national ID number merely to install. The existing full identity-document profile remains a separate optional user action because its current contract has different required fields.

Preferred integration:

1. After the official installer verifies successfully, load the installed Ed25519 Node ID using the existing Node Core identity store.
2. Register or reuse a private local `person` entity in `EntityIdentityRegistry` with the full name as its declared display name.
3. Link the entity to the real Node ID using the existing relationship mechanism.
4. Add a separately versioned Bitcoin association record that links the entity ID, Node ID, public Bitcoin address, network/address type, proof method, proof timestamp and verification status.
5. Keep a stable entity/profile ID across edits and updates. Generate IDs with a cryptographically secure random UUID/identifier mechanism; do not derive the Node ID or entity ID from the Bitcoin address.
6. Write atomically with restrictive permissions (directory `0700`, files `0600` where supported), reject malformed or unsupported schemas, and preserve the existing identity and association records during updater runs.
7. Add migration/backward-compatibility tests before changing any existing profile schema.

The record must clearly say that the name is declared and that Bitcoin proof verifies cryptographic key control only. Document evidence references, if later added, must remain unverified until a real issuer/document-verification procedure is implemented.

## 6. User-facing first-install workflow

The first option inside **03 · Install Node Core OS** must be:

**FIRST INSTALLATION OF NODE CORE OS byLAEV**

The form contains:

- Full name.
- Bitcoin private key (hexadecimal), masked input with show/hide control and a clear warning that it is a secret.
- Network/address type selector or the approved fixed first-release choice.
- A derived-address preview and explicit status of the key-control proof.

The first-install action remains disabled until all checks pass:

- native Termux detected;
- supported Android architecture detected;
- current user is not root;
- Node Core OS is not installed and no partial/residual installation is detected;
- the environment/installer preflight is ready;
- current official stable release metadata and install package digest are verified;
- full name is valid;
- Bitcoin key format and scalar are valid;
- address derivation succeeds for the selected scheme;
- challenge proof verifies and is not replayed.

A single click on the enabled **INSTALL NODE CORE OS** control may orchestrate the existing prepare/verify and execute steps, but must preserve both security boundaries internally:

1. Download the current official installer package over HTTPS and verify the exact published size and SHA-256 digest.
2. Re-fetch current release metadata and re-hash the staged package immediately before execution.
3. Safely extract only the expected canonical package files; reject traversal, symlinks, special files, excessive file counts and expanded size.
4. Execute only `bash installer/install.sh` from the verified package, as the unprivileged Termux user, without `sudo`, root or arbitrary browser-supplied command strings.
5. Display actual stdout/stderr, progress, timeout and exit status in a visible in-page terminal panel.
6. Verify the installed version, launcher, expected files, private runtime, Ed25519 NODE ID and required smoke tests.
7. Commit the pending public identity association to the private Node Core OS identity directory, linked to the actual installed Node ID.
8. Re-read the persisted record and verify its permissions, schema, address and node linkage.
9. Open Node Core OS through the installed canonical launcher, not an assumed development checkout.

If installation succeeds but the post-install association step fails, report **INSTALLATION COMPLETE — IDENTITY LINK PENDING**, preserve the valid installation, and offer a retry for association. Do not rerun a fresh installer over an existing installation.

If any installer or verification step fails, report the real error and non-zero exit status. Never display a success badge based only on process start or HTTP response.

## 7. Installation terminal and launch behavior

Reuse the existing installer job model and output polling endpoints. The installation view must resemble a terminal but display the actual captured process output, not fabricated text.

Requirements:

- Show the logical command `bash installer/install.sh` and the verified release version/commit before execution.
- Stream/poll the actual installer output and show timestamps, status, timeout and exit code.
- Keep output size and execution duration bounded.
- Do not expose the local session token, key material, private file paths beyond what is operationally necessary, or full profile data in generic logs.
- Do not allow arbitrary command input through the installation API.
- Keep install execution and the interactive Node Core application terminal as different process/session types.
- After verification and identity association, launch the installed Node Core OS entry point (prefer `~/.node-core/bin/node-core`) in the interactive PTY. Do not assume `$HOME/Node-Core-OS/main.py` exists on a clean installation.
- Update `start_node_core_terminal` and its tests so an installed node launches the canonical installed launcher. A development-checkout fallback, if retained, must be explicit and must never be mistaken for an installed product.

## 8. Main-menu header and status

After the new installation completes, the Node Core OS main menu must display:

- Node Core OS byLAEV branding;
- the persisted public Bitcoin address;
- the existing Ed25519 technical Node ID (where the menu already displays it);
- declared-name/association status without claiming civil identity verification.

The Bitcoin address is public information. The private key is never displayed. Truncate the address only for layout; provide an explicit copy/show-full-address action where appropriate. If the record is absent, invalid or revoked, show the correct state rather than fabricating an address.

## 9. Update workflow remains separate

The existing **04 · Update Node Core OS** flow remains independent from first installation.

- Require a complete, verified existing installation.
- Use only the official updater package and its SHA-256 receipt.
- Never request or accept a Bitcoin private key during update.
- Preserve Node ID, entity/profile IDs, Bitcoin address association, identity documents, configuration, storage, Kubo/IPFS repository, Lobby state and certificates.
- Verify before/after hashes or structured records for all protected data in tests.
- Do not downgrade or overwrite an ambiguous/partial installation.
- If an update fails, use the canonical updater rollback contract; do not rewrite identity association records as a recovery shortcut.

## 10. Implementation phases and task order

### Phase 0 — Baseline and release coherence

- [ ] Reconfirm branch head and diff against `main`.
- [ ] Run the existing Termux Lobby test workflow before changes.
- [ ] Run the existing identity profile, node identity, association and entity registry tests.
- [ ] Reconcile README release statements with the actual GitHub Releases API.
- [ ] Inspect the exact `v1.5.6` install/update archives and their source commit; record whether they contain the latest approved installer and identity changes.
- [ ] Define the next version/tag and verified publication path after the feature is implemented.

**Exit:** baseline tests and exact release provenance are recorded; a known-good package source is identified.

### Phase 1 — Identity and Bitcoin proof specification

- [ ] Approve the first-release Bitcoin network and address type.
- [ ] Approve exact accepted input format (proposed: 64 hex characters / 32-byte scalar).
- [ ] Select the proof format and define exact signed bytes, domain separation, nonce expiry and replay behavior.
- [ ] Evaluate the browser crypto library, exact version, license, browser support, bundle and reproducible build.
- [ ] Define the public association JSON schema and migration behavior.
- [ ] Document the meaning and limits of `declared`, `derived`, `control_verified` and `not_verified`.

**Exit:** code-level contracts and test vectors are fixed before frontend/backend implementation.

### Phase 2 — Bitcoin cryptographic module

- [ ] Add a small isolated address derivation/proof module; keep it separate from Ed25519 node identity.
- [ ] Vendor and pin the reviewed browser crypto bundle; remove all runtime CDN/network dependency.
- [ ] Validate raw key length, hex alphabet and scalar range.
- [ ] Derive the public key and exact approved address format.
- [ ] Sign a domain-separated, one-time challenge.
- [ ] Verify proof and address binding with the backend's existing cryptographic runtime.
- [ ] Clear input and temporary buffers best-effort.
- [ ] Add known-answer vectors and negative tests from independent reference implementations.

**Exit:** independently tested address derivation and proof verification, with evidence that raw secrets are never persisted or transmitted.

### Phase 3 — Local identity association

- [ ] Reuse `EntityIdentityRegistry` for the person entity and local node reference.
- [ ] Add a dedicated versioned Bitcoin address association store; do not repurpose `IdentityAssociationStore` for a different key algorithm.
- [ ] Add challenge issue/complete endpoints protected by the Lobby's existing HTTPS/session-token/Origin/Host controls.
- [ ] Add schema validation, atomic writes, `0700`/`0600` permissions, replay protection and safe error handling.
- [ ] Add a pending-association mechanism that stores no private key.
- [ ] Add tests for multiple nodes using one address, unique node/entity IDs, wrong key, replay, expiry, tampering and persistence.

**Exit:** a declared person entity can be linked to several unique nodes, with separately verified Bitcoin key control and no secret retention.

### Phase 4 — First-install UI and orchestration

- [ ] Place first installation as the first item in the install panel.
- [ ] Add masked full-name/Bitcoin-key inputs and selected address-format display.
- [ ] Add derived address and challenge verification feedback.
- [ ] Keep the install button disabled until every readiness condition is true.
- [ ] Orchestrate prepare, digest verification, latest-release revalidation and execution from the single explicit install action.
- [ ] Render actual installer stdout/stderr in the terminal panel with progress and a truthful final status.
- [ ] Prevent duplicate concurrent first-install requests.
- [ ] Provide clear recovery states for installer failure and identity-finalization failure.

**Exit:** a clean first install can be initiated through the Lobby without a manually copied shell command.

### Phase 5 — Core menu integration

- [ ] Persist the Bitcoin address association after Node ID verification.
- [ ] Display the public Bitcoin address and current identity status in the main-menu header.
- [ ] Preserve existing menu behavior and current Ed25519 Node ID.
- [ ] Add copy/full-address handling without exposing the secret.
- [ ] Ensure diagnostics and report export redact all private and personal fields.

**Exit:** the first installed main menu displays the actual stored address associated with the actual Node ID.

### Phase 6 — Canonical install/update and packaging

- [ ] Confirm the official install package contains every new identity module, schema, static browser asset where needed, and tests required for verification.
- [ ] Keep the single `installer/install.sh` path and Termux-native dependency strategy.
- [ ] Keep update package changes separate and ensure identity records are preserved.
- [ ] Update installer verification and updater regression checks for new modules/schema.
- [ ] Update `compatibility/termux/README.md`, `docs/INSTALLER.md`, `docs/DEPENDENCIES.md` and identity documentation.
- [ ] Regenerate the official release archives and checksums from the approved commit.

**Exit:** the published package matches the exact approved commit and the Lobby can verify its contents and digest.

### Phase 7 — Automated and physical-device validation

- [ ] Extend `compatibility/termux/tests/test_server.py`, release metadata tests and `test-lobby.sh`.
- [ ] Extend Node Core identity, profile/entity, installer and updater tests.
- [ ] Add secret-leak scans over logs, reports, terminal output, storage, temporary files and test fixtures.
- [ ] Test no-network/remote-egress behavior during private-key use.
- [ ] Test clean install, duplicate install prevention, partial-install handling, failed download, digest mismatch, unsafe archive, process timeout, missing dependencies, invalid key, wrong key, expired/replayed challenge and failed post-install association.
- [ ] Test update preservation of Node ID, Bitcoin association, profile/entity IDs, storage, configuration, Kubo/IPFS and Lobby certificates.
- [ ] Run automated CI and record exact commit, test commands, pass/fail results and workflow URLs.
- [ ] Run the bootstrap, first install, launch, update and rollback on a physical Android ARM64 Termux device.
- [ ] Verify a second fresh installation using the same Bitcoin key receives the same address but a different Node ID and entity/installation ID.

**Exit:** all automated tests pass and physical-device evidence is recorded. CI alone is not a physical Termux test.

### Phase 8 — Acceptance and release

- [ ] Review the diff and security boundaries.
- [ ] Confirm no private key or real personal data appears in source, fixtures, reports or workflow logs.
- [ ] Confirm release artifacts and checksums correspond to the approved commit.
- [ ] Update implementation status using evidence-backed wording.
- [ ] Publish the approved release and update the Lobby release compatibility documentation.

**Exit:** the feature can be described as implemented only to the extent supported by code, automated tests, exact release provenance and physical-device evidence.

## 11. Test matrix

| Area | Positive tests | Negative/regression tests |
|---|---|---|
| Bitcoin input | valid 32-byte scalar; known address vectors | invalid hex, wrong length, zero, order-or-higher scalar |
| Address derivation | approved network/type produces reference address | network/type mismatch; wrong public key/address |
| Proof of control | correct key signs fresh challenge | wrong key, invalid signature, changed message, expired nonce, replay |
| Secret privacy | only public address/key/proof persists | key absent from API requests, logs, terminal, temp files, reports and disk |
| Identity model | declared name + entity + multiple node references | identity data mislabeled as legally verified; duplicate IDs |
| Lobby API | authenticated local HTTPS challenge and association | missing token, wrong Origin/Host, HTTP mutation, malformed body, oversized body |
| First install | verified package installs and links actual Node ID | installed/partial node, invalid release, digest mismatch, unsafe archive, duplicate request |
| Terminal | real output, exit code and timeout visible | fabricated success, lost stderr, unbounded output/session |
| Main menu | persisted address matches association record | missing/corrupt/revoked record or wrong node linkage |
| Update | data and identity survive update | update asks for key, identity overwritten, downgrade, ambiguous rollback |
| Termux | native ARM64, normal user, Termux packages | root, unsupported architecture, Linux wheel, missing package/network |

All automated fixtures must use synthetic names, keys and addresses. Never commit or place a real private key or real identity document in a test fixture.

## 12. Definition of done

The first installation is functionally complete only when:

- the first-install option is the first option in the Lobby install menu;
- the form derives and verifies the Bitcoin association using the approved network/address format;
- the private key is not transmitted to the server or persisted anywhere;
- the install button is blocked until the complete preflight passes;
- one explicit install action downloads, verifies and executes the official install package;
- actual process output and final exit/verification results are visible;
- the resulting node has a valid persisted Ed25519 NODE ID;
- a private local person/entity record is linked to that actual NODE ID;
- the Bitcoin address association is persisted and independently revalidated;
- the main menu displays the persisted public address;
- a second node can use the same Bitcoin key/address and still receives a distinct Node ID and entity ID;
- update preserves all identity and persistent data and never asks for the private key;
- CI and physical Termux ARM64 validation pass;
- release artifacts are traceable to the exact approved source commit.

**No completion claim is valid from a rendered button, a successful HTTP response, a downloaded archive, or a process-start event alone.**
