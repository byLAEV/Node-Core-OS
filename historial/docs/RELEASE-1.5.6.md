# Node Core OS 1.5.6 — Release Candidate and Publication Checklist

**Status:** preparation; not yet approved.  
**Version:** `1.5.6`  
**Repository:** `byLAEV/Node-Core-OS`

## Strict publication contract

The GitHub Release must contain exactly two downloadable files:

- `node-core-os-install-1.5.6.tar.gz`
- `node-core-os-update-1.5.6.tar.gz`

No checksum files, platform/architecture variants, duplicate BIOS packages or third archive. SHA-256 and SHA-512 digests belong in the Release notes. Only `.github/workflows/bios-release-packages.yml` publishes. `.github/workflows/package-installers.yml` is validation-only.

## Included scope

- One canonical installer: `bash installer/install.sh`, detecting GNU/Linux and native Termux ARM64 internally.
- One self-contained updater: extract its archive and run `bash update.sh`.
- Platform-native dependencies, architecture-aware Kubo download, retry/resume and checksum verification.
- Protected update/recovery preserving identity, configuration, local storage and Kubo repository.
- Ordinary-user-only installation/update/recovery; no root or sudo.
- Ed25519 LAN identity proof, mutual peer authentication and restricted identity/status TLS sessions.
- Configurable TLS handshake deadline (60 seconds by default), post-handshake inactivity timeout (30 seconds by default), tracked in-flight sockets and shutdown cancellation.
- CDD intent-lobby hardening: 1 KiB ticket request limit, strict JSON, duplicate-key and content-type rejection, destination validation.
- Operator credential lifecycle and repository metadata consistency.

## Validation boundaries

- Automated GNU/Linux packaging targets Ubuntu 24.04 x86_64.
- Non-root Linux install/update checks include Ubuntu 24.04, Debian 13 and Fedora 44.
- Termux uses Android ARM64 native packages; physical-device smoke testing remains separate from CI.
- HashPaper and P2P Contracts are suspended and excluded; skipped checks are not successful.
- No worldwide peer discovery, production global rendezvous, human identity verification, production anti-bot or deployed ZK system is claimed.

## Required before publication

1. Repository coherence, shell syntax, Python compilation and regression suites.
2. Fresh install, update, rollback/recovery and persistent-data preservation.
3. Linux distribution E2E without root/sudo.
4. Termux ARM64 dependency tests; report physical-device smoke-test status honestly.
5. Identity, P2P, replay, malformed input, certificate, Kubo and CDD tests.
6. Build exactly two archives from the exact final release commit.
7. Verify offline updater E2E, archive contents, embedded source commit and both SHA-256/SHA-512 digests.
8. Verify canonical tag points to the approved commit and Release contains exactly two assets.

## Publication sequence

1. Merge the single-installer/updater contract after CI passes.
2. Validate the exact final main commit.
3. Verify no stale assets exist on the intended Release.
4. Create/verify `v1.5.6` against the exact approved commit; do not silently rewrite the historical `1.5.6` tag.
5. Trigger the one official release workflow.
6. Verify exactly two archives and checksums embedded in Release notes.

**Decision:** publication remains blocked until the final commit, tag, CI and two downloadable assets are verified.
