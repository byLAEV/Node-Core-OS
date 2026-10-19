# Node Core OS 1.5.4 — Release readiness

Status: **PREPARATION ONLY — NOT RELEASED**

This checklist tracks the next installer publication. Do not create the `v1.5.4` tag or publish a release until every required item below has evidence attached.

## Installer package

- [ ] Set `VERSION` to `1.5.4` only after release approval.
- [ ] Run `.github/workflows/package-installers.yml` from the release commit.
- [ ] Verify both generated archives: fresh installer source and existing-install updater.
- [ ] Verify SHA-512 checksum files against the downloaded archives.
- [ ] Install from scratch on Ubuntu 24.04 x86_64.
- [ ] Upgrade an existing installation and verify rollback/error behavior.
- [ ] Confirm release assets exclude HashPaper, as required by the packaging workflow.

## Local P2P presence and signed manifest

- [ ] Two independent nodes discover each other on the same LAN.
- [ ] Both establish authenticated sessions and report the same online-node count.
- [ ] Each participating node signs the exact same canonical manifest.
- [ ] Each node verifies every signature against the public key bound to its node identity.
- [ ] The menu shows consensus as confirmed only after every roster member has a valid signature.
- [ ] Missing, duplicate, invalid, stale, or tampered signatures leave consensus unconfirmed.
- [ ] Disconnect one node; its online session expires and the manifest is recomputed in a new epoch.
- [ ] Three-node integration test passes in GitHub Actions.

## CI and publication

- [ ] Full terminal test suite passes on the release commit.
- [ ] Installer end-to-end workflow passes on the release commit.
- [ ] Three-node P2P integration test passes on the release commit.
- [ ] Release workflow creates both archives and checksum files.
- [ ] Download release assets and independently verify checksums.
- [ ] Only then publish the GitHub Release and announce the version.

## Current limitation

The existing signed-manifest module verifies a proposed roster and signatures locally. That alone is not a distributed consensus protocol: transport-level proposal exchange, signature collection, timeout/epoch handling, and integration with the main-menu status must be completed and tested before claiming unanimous online-node consensus.

The last validated CI result applies to the commit tested by those workflows; it does not prove that the unfinished distributed-manifest feature works end to end.
