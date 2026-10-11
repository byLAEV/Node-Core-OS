# Changelog

All notable changes to Node Core OS are documented here.

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

