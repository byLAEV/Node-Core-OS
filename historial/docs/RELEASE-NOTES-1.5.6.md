# Node Core OS byLAEV — 1.5.6 Release Notes

**Draft — not yet published**

## Exactly one installer and one updater

Every release has exactly two downloads:

- `node-core-os-install-1.5.6.tar.gz` — the single fresh installer.
- `node-core-os-update-1.5.6.tar.gz` — the single self-contained updater.

Fresh install: extract the installer and run `bash installer/install.sh`.  
Existing installation: extract the updater and run `bash update.sh`.

Both commands run as the normal user, never root or sudo. The same installer detects GNU/Linux and native Termux ARM64 and selects compatible dependencies internally. There are no separate distro or architecture downloads. SHA-256 and SHA-512 values are embedded in the GitHub Release notes, not published as separate files.

## What is new in 1.5.6

### Linux terminal installation and updates
- Unified GNU/Linux and native Termux ARM64 installation path.
- Platform-specific Python dependency selection; no GNU/Linux wheels installed on Android.
- Architecture-aware Kubo acquisition, retries, resumable transfers and checksum validation.
- Protected updater and recovery improvements preserving identity, configuration, local storage and Kubo/IPFS repository.
- Ordinary-user-only installation, update and recovery.

### Identity and peer security
- One-shot Ed25519 LAN identity proof and strict bounded validation.
- Mutual peer authentication and malformed/replay input rejection.
- Restricted identity/status TLS sessions with configurable handshake deadline (60 seconds by default), configurable post-handshake inactivity timeout (30 seconds by default), tracked connections and shutdown cancellation.
- Lifecycle tests for authenticated requests, stalled handshakes, worker recovery, shutdown and revocation.
- Discovery, authentication, trust and authorization remain distinct. A cryptographic node identity is not civil identity verification.

### CDD gateway
- Separate 1 KiB ticket-consume JSON limit.
- Require application/json and reject duplicate JSON keys.
- Validate destination paths and emit fixed public IPFS gateway links.
- Single-process in-memory MVP; not production anti-bot or human identity verification.

### Operator and repository consistency
- GitHub operator credential lifecycle hardening and token refresh/rotation.
- Metadata/manifest consistency and release-version checks.

## Compatibility and limitations
- Automated package build targets Ubuntu 24.04 x86_64.
- Non-root Linux install/update CI includes Ubuntu 24.04, Debian 13 and Fedora 44.
- Termux uses native Android ARM64 packages; a physical Android device smoke test is separate from CI.
- HashPaper and P2P Contracts are suspended and excluded from release claims.
- No worldwide native peer discovery, production global rendezvous, public stable SDK, deployed ZK proof system or human identity verification is claimed.

## Integrity and publication record
The final Release must contain exactly the two archives listed above. SHA-256 and SHA-512 digests for each archive are embedded in these notes. The final announcement must identify the source commit, CI evidence, intentionally skipped workflows and physical Termux test status.

**Publication status:** blocked until final commit, tag, CI, two assets and checksums are verified.
