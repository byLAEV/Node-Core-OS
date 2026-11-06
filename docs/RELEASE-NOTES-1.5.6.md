# Node Core OS byLAEV — 1.5.6 Release Notes

**Draft — not yet published**

**Version:** 1.5.6  
**Project:** Node Core OS byLAEV  
**Repository:** https://github.com/byLAEV/Node-Core-OS/

> These notes describe the intended 1.5.6 release scope. They are not an announcement that the release is available. Final commit, CI results, tag, downloadable assets, and checksums must be verified before this draft is marked final.

## Overview

Node Core OS 1.5.6 consolidates the Linux-terminal installation path, improves platform-specific dependency handling, strengthens the updater and recovery behavior, and hardens technical node identity and peer authentication.

The project continues to combine user-owned local storage with Kubo/IPFS integration as a foundation for protocols and applications. Node Core OS is an application/runtime layer for Linux terminal environments; it does not replace the host Linux distribution.

## Main changes

### Unified Linux terminal installation

- Establishes `bash installer/install.sh` as the canonical installer entry point.
- Uses a shared Linux-terminal compatibility and capability-detection path for GNU/Linux and native Termux ARM64.
- Selects platform-native Python dependencies for Termux rather than assuming GNU/Linux binary wheels are compatible with Android.
- Handles architecture-specific wheel mismatches with a controlled fallback.
- Improves Termux virtual-environment migration and preserves existing user-owned application data.
- Routes fresh installation and existing-install handling through the unified installer path while retaining the legacy Termux command as a compatibility alias.

### Updater and recovery

- Improves dependency preparation for direct update operations in Termux.
- Enforces the minimum supported cryptography dependency.
- Strengthens recovery checks and compatibility handling for older installations.
- Preserves existing identity, configuration, local storage, and Kubo/IPFS data during supported update operations.
- Keeps installation, update, recovery, and runtime execution in the normal user's account. Root and sudo are not supported.

### Technical identity and peer security

- Adds a one-shot Ed25519 LAN identity-proof protocol.
- Applies strict bounded validation to identity-proof fields.
- Hardens mutual peer authentication and handshake validation.
- Adds rejection coverage for malformed, noncanonical, oversized, and replayed protocol input.
- Maintains the separation between peer discovery, authentication, trust, and authorization.

A discovered peer is not automatically trusted or authorized. A technical node identity proves control of a cryptographic key under the defined protocol; it does not independently verify a person's civil identity.

### Repository and release consistency

- Aligns runtime dependency declarations, installer documentation, compatibility manifests, and repository contracts with executable behavior.
- Adds regression checks for metadata drift.
- Validates that the version in `VERSION` matches the version tag used by the release workflow.
- Supports the version-tag naming forms accepted by the release workflow, with or without a leading `v`.

### Operator identity controls

- Improves the GitHub operator credential lifecycle, including refresh-token rotation, access-token refresh, account revalidation, and BIOS/API refresh controls.

## Storage and networking

- Local storage remains under the user's Node Core OS data area.
- Kubo/IPFS remains an external content-network integration; a CID identifies content but does not prove authorship, guarantee permanent availability, or grant authorization.
- Kubo peer connectivity and native Node Core OS P2P peer authentication are separate states.
- The release does not claim worldwide native peer discovery unless an actual rendezvous/bootstrap service is configured and running.

## Compatibility and validation boundaries

- Automated GNU/Linux release packaging targets Ubuntu 24.04 x86_64.
- CI includes real non-root installation/update lifecycle checks on the distributions declared in the current workflow matrix, including Ubuntu 24.04, Debian 13, and Fedora 44.
- Termux uses its Android ARM64 native dependency path. Automated CI is not a substitute for a physical Android/Termux device smoke test.
- The release does not claim every Linux distribution, terminal emulator, shell, or architecture has been individually tested.
- Suspended HashPaper and P2P Contracts workflows are excluded from release claims. A skipped workflow is not a successful test.

## Not included or not claimed

- PR #206 and PR #207 remain separate draft P2P restricted-session work and are not included in this release candidate.
- PR #184 is an older divergent branch and is not part of this release.
- PR #205's CDD intent-lobby changes are pending final CI/review and are not described as shipped here. If that PR is integrated before the release freeze, these notes and the final changelog must be updated to describe its exact shipped scope and limitations.
- No production-grade global rendezvous network, public stable API/SDK, verified human identity service, service marketplace, participant income guarantee, production anti-bot protection, or deployed zero-knowledge-proof system is claimed.

## Installation

The canonical installer entry point is:

```bash
bash installer/install.sh
```

Run as the ordinary installation user. Do not use root or sudo.

## Expected release downloads

The release workflow is expected to attach the following files after the final version tag is validated:

- `node-core-os-installer-1.5.6.tar.gz`
- `node-core-os-installer-1.5.6.tar.gz.sha512`
- `node-core-os-updater-1.5.6.tar.gz`
- `node-core-os-updater-1.5.6.tar.gz.sha512`

Do not download or distribute a package until it is attached to the official Release and its SHA-512 checksum has been verified.

## Final validation record

The final release announcement must include:

- Exact final Git commit SHA and tag target.
- Links to completed required GitHub Actions runs.
- Explicit list of intentionally suspended/skipped workflows.
- Installer and updater asset links.
- Successful SHA-512 verification for each archive.
- Confirmation that the updater archive identifies the same source commit as the installer package.
- Physical Termux/Android smoke-test result, or an explicit statement that this test remains outstanding.

**Publication status:** blocked until the final commit, CI, tag, package assets, and checksums are verified.
