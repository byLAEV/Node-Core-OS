# Node Core OS 1.5.6 — Release Candidate and Publication Checklist

**Status:** preparation document; not a release approval.  
**Target version:** `1.5.6`  
**Repository:** `byLAEV/Node-Core-OS`

## 1. Release identity

- `VERSION` on the current main baseline is `1.5.6`.
- The previously published GitHub Release `1.5.6` was removed for correction.
- The Git tag `1.5.6` still exists and points to historical commit `c3a8f789580d193fff0d4ecb8eea4a83baee1de8`.
- The main baseline reviewed for this preparation was `82961014399e79ce47ab2e9f602939fa504091b8`.
- The historical tag must not be used as the final package source. Before publication, the version tag must be reconciled to the exact approved release commit and verified again through GitHub's tag and release APIs.
- Do not silently force-move a tag. Record the old and new commit IDs in the release report and confirm the tag target before building assets.

## 2. Release scope

The current main-line 1.5.6 candidate contains the following work:

### Linux terminal installer and updater

- One canonical installer entry point: `bash installer/install.sh`.
- Unified GNU/Linux and native Termux ARM64 environment detection and dependency preparation.
- Native Termux Python dependency selection for cryptography rather than assuming GNU/Linux wheels are portable to Android.
- Safer handling of architecture-specific wheels and fallback behavior when a bundled wheel does not match the target platform.
- Migration of existing Termux virtual environments while preserving user data.
- Unified fresh-install and existing-install routing, with the legacy Termux command retained as a compatibility alias.
- Updater preparation of Termux dependencies and minimum cryptography version checks.
- Installation, update, recovery, and runtime remain ordinary-user operations. Root and sudo are not supported.

### Identity and native peer security

- One-shot Ed25519 LAN identity proof protocol.
- Strict bounded validation of identity proof fields.
- Mutual peer-authentication hardening, strict handshake roles, and replay/malformed-frame regression coverage.
- Discovery, authentication, authorization, and trust remain distinct concepts. A discovered peer is not automatically trusted or authorized.

### Repository and release consistency

- Runtime dependency and installer documentation aligned with the code.
- Machine-readable repository contract and regression coverage for metadata drift.
- Release workflow validates that the tag version matches `VERSION`.
- The package workflow accepts version tags with or without a leading `v`.

### Existing identity and operator controls

- GitHub operator credential lifecycle hardening, including refresh-token rotation, access-token refresh, account revalidation, and BIOS/API refresh controls.
- Identity profile timestamp test correction after node association.

## 3. Platform and compatibility statements

- Automated release packaging targets Ubuntu 24.04 x86_64 GNU/Linux.
- GNU/Linux CI includes native Linux installation and update checks using an ordinary unprivileged user.
- Termux is supported through its native Android ARM64 dependency path in the installer code and CI checks.
- A physical Termux/Android device smoke test is still a separate acceptance requirement. CI must not be described as a physical-device test.
- Do not claim all Linux distributions, shells, terminal emulators, architectures, or Android devices have been individually tested. Use the compatibility manifest and the actual CI matrix as the source of truth.
- Kubo/IPFS is an integration dependency. A successful Kubo CI run does not prove global availability, permanent pinning, or worldwide Node Core OS peer discovery.

## 4. Explicit exclusions and limitations

- PR #206 is a draft architecture record and is not included in the current main release candidate.
- PR #207 is draft implementation work for restricted identity/status sessions. It is not part of this release until independently reviewed, integrated, and accepted.
- PR #184 is an older divergent branch with failed checks; it must not be merged as a separate release change.
- HashPaper and P2P Contracts workflows marked suspended are excluded from release claims. A skipped workflow is terminal, but it is not a successful test.
- This release does not claim production-grade global P2P rendezvous, worldwide native peer discovery, a public stable API/SDK, human identity verification, a production anti-bot service, a marketplace, or zero-knowledge proof deployment.

## 5. Candidate changes awaiting validation

PR #205 proposes a CDD intent-lobby gateway correction:

- It separates the small ticket-envelope request limit from the signed protected-origin upload limit.
- It adds an independent 1 KiB limit for the consume-ticket request.
- It adds strict JSON parsing that rejects duplicate keys and requires `application/json`.
- It adds regression tests for oversized ticket bodies, duplicate JSON keys, replay protection, and content-type validation.
- It corrects the documentation so it does not claim that the lobby HTML is retrieved through local Kubo when the implementation only generates fixed public gateway links.

PR #205 must be reviewed and all active checks for its final head SHA must complete successfully before it can be included. The two suspended P2P Contracts workflows remain skipped and must be identified as such in the release report.

## 6. Required pre-publication validation

All checks below must be attached to the exact final release commit, not to an earlier PR head or an old tag.

1. Repository coherence tests: `VERSION`, README, changelog, manifests, installer specification, dependency contract, and package metadata agree.
2. Shell validation: all supported installer and updater shell scripts pass syntax checks and ordinary-user contract checks.
3. Python validation: compilation and full relevant unit/regression suites pass in the private application environment.
4. Linux installer E2E: fresh install, update, rollback/recovery, and preservation of existing identity/configuration/storage as applicable.
5. Linux distribution E2E: each distribution in the published CI matrix completes without root or sudo.
6. Termux checks: Android ARM64 dependency selection and environment migration pass CI; record a separate physical-device smoke test if available.
7. Identity/security: Ed25519 proof, peer authentication, malformed input, replay, certificate adversarial, and relevant network-domain checks pass.
8. Kubo: user-only integration and byte-for-byte content retrieval checks pass.
9. BIOS: package generation and menu regression tests pass.
10. CDD: signed policy, body limits, ticket size, duplicate JSON keys, content type, ticket replay, and gateway integration tests pass if PR #205 is included.
11. Suspended workflows: list each skipped workflow by name and state why it is suspended. Never relabel skipped as passed.
12. Package build: generate installer and updater archives from the exact release commit, verify the updater offline E2E, and verify each SHA-512 file.
13. Archive inspection: inspect package contents and ensure suspended application files are excluded as configured.
14. Release verification: confirm the Git tag points to the intended commit, the Release exists, all expected assets are attached, and the downloaded assets pass their SHA-512 checks.

## 7. Expected downloadable assets

The package workflow is expected to publish:

- `node-core-os-installer-1.5.6.tar.gz`
- `node-core-os-installer-1.5.6.tar.gz.sha512`
- `node-core-os-updater-1.5.6.tar.gz`
- `node-core-os-updater-1.5.6.tar.gz.sha512`

The exact asset list must be confirmed from the completed workflow and Release page. Do not announce downloads or provide links before the assets are visible and verified.

## 8. Publication sequence

1. Complete review and merge only approved release-scope PRs.
2. Reconcile README and changelog against the exact code that will ship.
3. Run all required workflows on the final main commit and preserve the run links/logs.
4. Verify the package workflow on the exact final commit.
5. Reconcile the historical `1.5.6` Git tag to the approved commit using a recorded, deliberate tag operation.
6. Trigger the version-tag package workflow.
7. Verify installer/updater archives, SHA-512 files, Release asset links, and the embedded source commit.
8. Publish the formal release notes and user-facing installation/update instructions.

## 9. Current decision

**Not yet approved for publication.**

The main baseline has a substantial body of successful Linux and security CI evidence, but the old version tag is stale, the release assets must be regenerated, the final release-scope PR #205 has new checks in progress, and a physical Termux smoke test remains separate from CI. Publication approval requires the exact final commit and downloadable assets to be verified.
