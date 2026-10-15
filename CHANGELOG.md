# Changelog

All notable changes to Node Core OS are documented here.

## Node Core OS [1.5.2] - 2026-10-15

- Make LAN discovery and worldwide discovery independent, explicitly labeled states in the network menu.
- Show discovered identities separately from authenticated inbound sessions and never treat discovery as trust or authorization.
- Preserve the existing user-level installation contract and existing local data during updates.
- Harden updater rollback reporting so recovery files are retained if automatic rollback fails.
- Add regression tests for symlinked application paths, commit markers, and release source paths.
- Align installer package names and release metadata with Node Core OS as a separate application; the Node Core updater package no longer bundles the HashPaper updater.
- Validate package archives and publish SHA-512 checksums through the version-tag workflow.
- Release validation targets Ubuntu 24.04 x86_64 GNU/Linux. Termux/Android is not declared supported by this release.


## Node Core OS [1.5.1] - 2026-10-15

- Add a consolidated Network / Nodes status dashboard for Kubo/IPFS and native authenticated P2P.
- Show each transport's local identity, direct/active peers, listener state, trusted and revoked peer counts, and independent error state.
- Keep Kubo/IPFS peer counts separate from native P2P sessions; do not imply a global network node count.
- Add regression tests for healthy status and partial failures when either transport is unavailable.
- Preserve existing menu options and ordinary-user operation; no root or sudo is required.

## Node Core OS [1.4.2] - 2026-10-13

- Allow the first P2P Contracts propagation to bootstrap from the validated genesis hash on a single node when no peer responds.
- Ask the operator to explicitly accept the genesis root hash before initializing logical block 1.
- Keep active-proposal conflict checks and require peer responses for later propagations when a local manifest already exists.
- Add regression tests for single-node genesis bootstrap, later propagation without peers, and active-proposal blocking.
- Add a dedicated local-only request and manifest creation path that does not query PubSub or require peer responses.
- Label single-node manifests as local and uncorroborated until other nodes verify them.
- Keep the bundled genesis manifest path anchored to the application module and verify its local storage copy.
- Add regression tests for multiple offline manifest sequences and CLI creation without peer discovery.
- Run the new P2P CLI regression tests in CI and as part of updater validation.
- Preserve ordinary-user-only operation; root and sudo are not required.


## Node Core OS [1.4.1] - 2026-10-13

- Anchor the first Node Core P2P Contracts manifest to the bundled genesis reference.
- Validate the synchronized genesis manifest and require block 1 to reference the configured Bitcoin Mainnet genesis hash.
- Reject first remote manifests that do not reference the expected genesis.
- Require the genesis manifest in installation and update packages.
- Extend real-Kubo three-node tests to verify block-1 genesis references and manifest convergence.
- Keep installation, update, and runtime operations in the ordinary user's account; root and sudo are not required.

## Node Core OS [1.3.0] / Node Core P2P Contracts [1.0.0] - 2026-10-12

- Include Node Core P2P Contracts in the default Node Core OS installation package.
- Version P2P Contracts as 1.0.0 and Node Core OS as 1.3.0.
- Make the installer fail clearly if the P2P Contracts entry point, CLI, version file, or tests are missing.
- Validate the installed P2P Contracts version during installation.
- Extend the Ubuntu 24.04 installer E2E workflow to verify that P2P Contracts 1.0.0 and its real-Kubo integration test are present in every clean installation.
- Keep all install steps in the ordinary user's home directory; root and sudo are not used.

## Node Core OS [1.2.9] / HashPaper [0.3.5] - 2026-10-11

- Release the combined HashPaper create-and-timestamp operation as a versioned update so existing installations can receive it through the Node Core OS updater or the HashPaper-only updater.
- HashPaper option 1 now saves the original and immediately submits that exact file to the official OpenTimestamps client.
- Preserve the local original and report the failure if timestamp submission fails; do not claim submission or verification without evidence.
- Show the actual timestamp processing status and proof-file fingerprint, while distinguishing a pending Bitcoin attestation from a verified timestamp.
- Update installer end-to-end assertions and regression tests to cover the new workflow.
- Keep all installation and update operations in the normal user's account; preserve identity, configuration, local documents, .ots proofs, packages, records, and Kubo/IPFS data.

## Updater regression correction — 2026-10-11

- Fixed updater diagnostics contaminating the stdout value returned by `latest_commit`. Download progress is now sent to stderr, leaving stdout reserved for the validated commit SHA.
- Kept slash-containing branch refs intact in the GitHub API query parameter and URL-encoded the ref only for the fallback path endpoint.
- Silenced the expected JSON parser diagnostic when the read-only installer detector classifies deliberately malformed configuration as invalid.
- The prior CI failure was reproducible: progress text was captured alongside the SHA, then used to build invalid archive URLs. Re-run CI before merging to verify this fix.

## Official download fallback hardening — 2026-10-11

### Fixed
- Add a second official GitHub API route for Node Core OS commit metadata and accept the correct JSON shape returned by either the list endpoint or the single-ref endpoint.
- Add GitHub archive and official codeload fallbacks for Node Core OS updates, validating the archive before replacing the installed application.
- Pin the OpenTimestamps client to upstream release 0.7.2 and add PyPI, official GitHub tag archive, and official codeload fallback routes.
- Keep Kubo downloads on the official GitHub Releases and dist.ipfs.tech sources, with the archive and SHA-512 checksum always fetched from the same source.
- Update updater preservation tests to recognize the official metadata and archive fallback routes.

### Security
- No third-party mirrors are used.
- All installation and update work remains strictly user-level; no root, sudo, system package manager, or system-wide Python changes.
- Existing user data and Kubo/IPFS storage must be preserved if all download sources fail.

### Validation
- Added `docs/DOWNLOAD-SOURCES.md` describing upstreams, fallback order, integrity checks, and operational limits.
- CI must pass against this change before the PR is merged.

## User-only installer hardening — 2026-10-11

### Fixed
- Reject execution as UID 0 at the start of every top-level installer, updater, uninstaller, HashPaper installer, optional OpenTimestamps server installer, and sourced installer helper library.
- Fix updater metadata retrieval for branch names containing slashes by sending an encoded branch in the GitHub API query instead of treating the branch as a URL path.
- Validate the API response and commit SHA before publishing update metadata; remove temporary response files and fail with a clear diagnostic when the request or metadata is invalid.
- Keep update metadata writes atomic and never continue with a missing or invalid `latest-commit.json`.

### User-only contract
- No `sudo`, root execution, system package installation, or system-wide Python modification is permitted.
- All application files, virtual environments, metadata, launchers, and optional server source must be owned by the installing user and remain under that user's home directory.
- The updater's real-install E2E test uses a branch containing slashes, exercising the original failing case.


## Node Core OS [1.2.8] / HashPaper [0.3.4] - 2026-10-11

### Added
- Add an opt-in user-level installer for the official OpenTimestamps calendar-server source and its Python requirements.
- Document the official Python library, client, HashPaper proof workflow, pending-versus-confirmed semantics, and calendar-server operational prerequisites.

### Fixed
- Create the persistent HashPaper `proofs/` directory on fresh Node Core OS installs.
- Include all top-level installer scripts in Bash syntax validation, including the optional calendar-server setup helper.
- Keep the official OpenTimestamps client in its own private virtual environment; do not alter system Python.

### Safety and limitations
- The optional server setup only clones the upstream repository and installs its dependencies. It does not start a daemon, expose ports, create or fund a Bitcoin wallet, or claim that a calendar server is operational.
- A production calendar requires separately configured Bitcoin Core, wallet, calendar URI, secret material, monitoring, and network security.
- Real Termux installation and live calendar tests must still be executed on target environments before release approval.


## HashPaper [0.3.3] - 2026-10-11

### Fixed
- Validate that both the official `ots` command and its Python `opentimestamps` module are usable in the private user-owned virtual environment.
- Create the persistent `~/.node-core/hashpaper/proofs/` directory during installation.
- Reject symbolic-link and foreign-owned HashPaper runtime/data/launcher directories instead of writing through them.
- Keep HashPaper installation and dependency setup in the normal user context; root execution remains rejected.

### Validation
- Extend the HashPaper installer regression test to assert that the proofs directory is present and private.
- Real Termux and live public-calendar execution must be run on the target device; they are not claimed as passed by this change.

## [1.2.7] - 2026-10-11

### Added
- Show the original document SHA-256, exact local `.ots` file SHA-256, proof status, verification status, and calendar URLs immediately after timestamp operations.
- Display Bitcoin transaction IDs only when explicitly labelled in output from the official OpenTimestamps client.
- Release HashPaper 0.3.1 with clearer pending-proof evidence reporting.

### Safety
- A pending `.ots` proof remains distinct from a Bitcoin-confirmed proof.
- Local SHA-256 fingerprints identify exact bytes; they are not represented as OpenTimestamps-issued identifiers.
- Failed submissions do not fabricate proof files or identifiers.

## [1.2.6] - 2026-10-11

### Added
- Bundle HashPaper 0.3.0 as the default application in fresh installations and in every Node Core OS application update.
- Validate both Node Core OS and HashPaper version metadata before an update is marked successful.
- Run HashPaper compilation and unit tests during fresh installation as well as application updates.
- Report the bundled HashPaper version during updates, keeping the application code synchronized with the Node Core OS release.
- Include safe recovery from interrupted updater cleanup (PR #63), while preserving recovery evidence and user data.

### Validation
- Add Termux update regression assertions for Node Core OS 1.2.6 and HashPaper 0.3.0.
- Installer E2E asserts the default HashPaper version is 0.3.0 and exercises its interactive menu and Kubo integration.
- HashPaper Python matrix and standalone HashPaper updater regression remain part of CI.

## [1.2.3] - 2026-10-10

### Added
- Add end-to-end integration coverage for identity-association announcements across three independent Kubo nodes and convergence on one shared, locally stored, pinned report CID.
- Preserve machine-readable evidence for each node in the GitHub Actions artifact.
- Verify that clean installations include a valid application `VERSION` file and that the existing-install updater delivers the new version without replacing user data or Kubo assets.

### Fixed
- Correct the trailing newline in the three-node evidence summary so the downloaded `summary.json` remains valid JSON.

### Validation
- Three-node Kubo integration, GNU/Linux terminal CI, and Ubuntu 24.04 x86_64 installer E2E are required checks for this release.
- Installer and updater operations remain user-level and do not require root or sudo.

## [Unreleased]

### Added
- Document good-faith identity UX, privacy-by-default, declared-versus-verified status, and layered future security controls in `docs/IDENTITY-DESIGN-PRINCIPLES.md`.
- Add a local text-only identity profile under the Node Core BIOS, with explicit association to an available Kubo Peer ID.
- Show all locally saved identity fields in the main menu, including the document number, logical identity ID, and node association, while clearly marking network-consensus verification as not verified.
- Add optional date of birth, height in centimeters, and self-described gender fields, with input validation and explicit declared-data semantics.
- Release the identity-profile and updater integration as Node Core OS 1.2.2; require installer verification to find the identity-profile module and test that updates deploy it without replacing persistent data.
- Display the first-entry and last-updated timestamps for identity data in ISO-8601 UTC format.
- Add tests for local persistence, stable logical identity, node association, and private file permissions.

### Security and scope
- Profile data remains local and is not automatically sent to IPFS. Full-value display in the single-user local menu does not imply network publication or external disclosure.
- Entered identity data is marked declared, not verified. Issuer corroboration, holder verification, personhood checks, and duplicate prevention are not implemented by this profile.

## [1.2.1] - 2026-10-10

This is a maintenance and reliability release focused on safer user-level updates and recovery.

### Added
- Guard against starting another update while recovery artifacts from a failed rollback remain.
- Regression coverage for failed rollback and subsequent update attempts.
- Explicit preservation checks for the installed application, commit marker, local storage, Kubo/IPFS repository, executable, and configuration during updater failure scenarios.

### Changed
- Validate the remote Git commit identifier before attempting to install an update.
- Back up and restore the installed commit marker together with the application during rollback.
- Retain recovery files when rollback fails and report the recovery directory instead of claiming recovery succeeded.
- Refuse another update until retained recovery artifacts have been inspected.

### Validation
- GNU/Linux Terminal CI: passed for the current main commit before release preparation.
- Installer E2E on Ubuntu 24.04 x86_64: passed for the current main commit before release preparation, including user-systemd and no-user-systemd scenarios.
- The tests run as an unprivileged user and do not require root or sudo.
- Real-device Termux validation is not claimed by these Linux CI results.

### Scope and limitations
- This release does not replace the local storage directory, Kubo executable, or IPFS repository during an application update.
- A failed rollback retains recovery files for manual recovery. Do not delete them until the installed application and commit marker have been verified.
- Identity, reputation, distributed consensus, and other roadmap capabilities must not be interpreted as fully operational solely because they are documented.

