# Node Core OS byLAEV 2.0 — Priority register and fastest safe path

**Audit timestamp:** 2026-11-09 20:46 America/Costa_Rica (UTC-06:00)  
**Main baseline:** `2c2ef95521d60dfbdda05b2c55e1b80ac707bf03`  
**Published baseline:** `v1.5.6`; repository `VERSION` remains `1.5.6`.  
**Release decision:** 2.0 is **not ready to publish**.

This register prioritizes work by (a) blocking dependency, (b) amount of reusable work, (c) risk of rework, and (d) whether it is genuinely part of the agreed 2.0 product. It is designed to shorten the critical path without merging stale branches or treating skipped checks as passes.

## A. Priority summary

| Priority | Work item | Current evidence | Required result |
|---|---|---|---|
| **P0** | Finish PR #220 readiness control | Readiness audit job passes; 3 distro E2E jobs were still running at audit time | Finish checks, merge the audit/spec PR, keep release gate strict |
| **P1** | Port PR #214 relay reliability fix | Targeted relay, two-node Kubo, Linux distro tests and packaging pass on old head; branch 4 commits behind | Rebase/port to latest main; targeted tests green on new SHA; integrate |
| **P1** | Rebuild PR #217 as the real Lobby 2.0 foundation | 4 Python versions, static validation, installer E2E, Linux distro E2E, Termux Lobby CI and certificate catalog checks pass; physical Android job is skipped | Port to new main-based PRs, remove feature-ref and identity gate, add generic Linux support, device acceptance |
| **P1** | Implement Lobby-to-core install and repair workflow | Existing core installer/updater are reusable; complete Lobby control path not present in main | Preflight → approved package preparation → core install (incl. Kubo) → certificates → launch/status/repair/update |
| **P1** | Replace the release packaging contract | Current release workflow is hard-coded to v1.5.6 and exactly two legacy installer/updater assets | Lobby bootstrap + Lobby package + Core package + updater + checksums/SBOM/provenance |
| **P2** | Retire or supersede PR #213 | 16 commits ahead, 103 behind, dirty merge; proposes obsolete 1.5.7 bump | Do not merge branch; confirm useful changes already in main, close as superseded or port only a proven missing fix |
| **P2** | Decide on PR #218 Android APK | 7 commits ahead, 617 behind, draft; build failed due obsolete SDK package `tools`; APK contains a small read-only Lobby only | Not a 2.0 blocker because #217 already provides Termux:Widget; defer or port only if a native APK icon is explicitly retained |
| **P2** | Enforce repository governance | Branch-protection/ruleset read was unavailable to this connection | Verify main protection and require the release-critical checks |

## B. Exact PR conflict/error register

### PR #220 — readiness audit and workflow
- Head: `d831ac6b047bfa3250549a6a079b8df91c19c8e4`; base is current main; compare was 4 commits ahead and 0 behind.
- The readiness audit job passed. This is a **non-strict schema/evidence audit**, not proof that the product meets 2.0 acceptance.
- At audit time the Ubuntu 24.04, Debian 13 and Fedora 44 non-root install/update/uninstall jobs were still in progress.
- Ubuntu installer, GNU/Linux terminal, package build, certificate adversarial tests, Web2 report and two-node Kubo jobs had completed successfully.
- Several suspended cross-VM jobs were skipped. Those skips must not be reported as successful executions.
- **Action:** wait for the 3 distro jobs, review the resulting head SHA, then merge this documentation/control PR only when every applicable check on the exact head finishes satisfactorily. Keep strict mode for final release authorization.

### PR #214 — relay persistence and signed receipt timeout
- Head: `44efbbc97d017a5ad55a1bc79449ac4648bb8a16`; 5 commits ahead and 4 behind main; draft; GitHub reports mergeable/clean against its recorded base.
- Files affected: `node_core/p2p/service.py`, `node_core/relay_delivery.py`, and two P2P/replication tests.
- Actual code change: replace hard-link based relay inbox publication with an advisory `fcntl.flock` plus atomic `os.replace()`; extend the post-authentication secure-message receipt wait to 30 seconds; raise affected integration-test timeouts.
- Existing targeted Relay authentication/persistence test passed; two-node Kubo, Ubuntu/Debian/Fedora install/update, installer and package checks also passed on the old head. Several suspended multi-VM jobs were skipped.
- Main currently still contains hard-link publication in `persist_and_sign_receipt()` and uses the original P2P socket timeout through receipt generation; the patch is therefore not yet superseded.
- **Action:** P1 fast path. Port the four-file fix to a branch created from current main, run relay race/deduplication tests, signed receipt tests and the Linux/Termux test suites. Then mark ready and merge if checks and reviews pass. Preserve the existing no-overwrite contract and test concurrent same-run IDs.

### PR #217 — existing Termux Lobby and official installer
- Head: `b52c16259120122b2be17ec894abd324dc6d280a`; GitHub reports 223 commits ahead and 4 behind main; draft; 29 files changed (+6,759 / -7).
- Automated successes on the latest head include: Lobby Python 3.10/3.11/3.12/3.13, static repository contracts, package build, Ubuntu installer, Ubuntu/Debian/Fedora non-root install/update/uninstall, Linux three-node P2P, two-node Kubo, certificate catalog integrity, adversarial certificate tests, Web2 stress/acceptance.
- Native Android Termux ARM64 device validation was **skipped**, not passed. Suspended cross-VM tests were also skipped.
- The bootstrap `compatibility/termux/bootstrap-lobby.sh` defaults `DEFAULT_REF=feature/termux-local-lobby`. Production must use a stable release tag (or an explicit commit during RC testing), never a feature branch.
- `compatibility/termux/install-lobby.sh` is Termux-specific: it uses `pkg`, `$HOME/.shortcuts`, and native Termux paths. It does not provide the GNU/Linux distro package-manager preparation or XDG desktop launcher path required by 2.0.
- It provides a Termux:Widget shortcut. This can satisfy the mobile quick-launch requirement for the Termux profile; generic terminal apps need a documented CLI fallback, and graphical Linux needs a .desktop launcher.
- The PR's first-install flow couples core installation to a Bitcoin identity gate and includes changes to `node_core/identity/entity_registry.py`. That is out of scope for 2.0. Installation must initialize/preserve the existing technical node identity, but must not require Bitcoin onboarding or implement the later full identity project.
- Its Lobby certificate manager handles Lobby loopback TLS and peer-trust administration; its core P2P certificate function is inspection-only. This is not yet an implementation of installing/verifying core trust certificates.
- **Action:** do not merge the 223-commit branch wholesale. Create new branches from latest main and port in slices:
  1. Existing Lobby server/UI, loopback-only runtime, authentication and read-only inventory.
  2. Bootstrap and launchers: stable tag/commit-pinned download, Termux:Widget, XDG .desktop, CLI fallback.
  3. Platform adapters and preflight: Debian/Ubuntu apt, Fedora dnf, other distros only by explicit tested profile; Termux pkg; detect architecture, storage, permissions and capabilities. Show a plan and obtain explicit consent before host package changes.
  4. Official package stage/run: only invoke canonical installer/update scripts, validate exact release metadata and digests, safe archive extraction, bounded output/timeouts and post-install health.
  5. Tests and device acceptance.
  Remove Bitcoin gating and unrelated entity-registry scope from the 2.0 install flow. Do not install the eight documentary security profiles as if they were eight root certificates.

### PR #213 — 1.5.7 one-command updater / Termux fix
- Head: `b8a3ea4fa7f3fbb610fdc6861a42f460e93373a7`; 16 commits ahead, 103 behind; non-draft; dirty/conflicting; 15 files changed.
- Historical CI on the branch ran the distro installer/update, packaging, certificate and P2P checks successfully, but several suspended cross-VM jobs were skipped. Those old checks do not validate the current main merge result.
- The branch changes `VERSION`, Python package version and repository contracts to 1.5.7, adds a root-level `update.sh`, and creates 1.5.7 release notes. This conflicts with the agreed 2.0 architecture where the terminal bootstrap installs the Lobby and the Lobby installs/updates the core.
- Main already detects Termux on Android Python and includes regression tests for Android/Termux markers; the core detection fix is not a reason to merge this stale 1.5.7 release branch.
- **Action:** no direct merge and no 1.5.7 tag. Verify every unique code fix against main; port only a genuinely missing test or fix into the relevant 2.0 PR. Once verified superseded, close #213 as superseded rather than rebasing 103 commits.

### PR #218 — standalone Android APK launcher
- Head: `889f1e01ef5dd668b5bc2b786147ecad2475dce3`; 7 commits ahead, 617 behind; draft; 13 files.
- The historical build job `Build NODE Lobby Installer APK` failed in Android SDK setup: `sdkmanager tools` returned `Warning: Failed to find package 'tools'`. The workflow must stop requesting the removed SDK `tools` package and explicitly install only current platform/build-tools packages if APK is retained.
- Its own description says the APK launches a standalone read-only Lobby; full Node Core install/update/repair remains disconnected. The separate `termux-lobby/` server is HTTP-only, so it must not be treated as the production administrative service without equivalent authentication/transport protection.
- **Action:** defer from the 2.0 critical path. #217's Termux:Widget and the planned XDG/CLI launchers cover the current quick-launch requirement. If a native APK is retained as an optional add-on, rebase/port it to current main, fix SDK package selection, secure the transport, and validate on a physical Android device separately. It must not delay the CLI/Lobby release.

## C. Fastest safe execution order

### Sprint 1 — close quick, independent blockers
1. Complete #220's running distro jobs; merge #220 after all applicable checks on its latest SHA pass.
2. Port #214 onto current main; run focused relay race/persistence and signed-receipt tests plus full Python/Termux regression; merge.
3. Close #213 as superseded after recording that its useful Termux detection behavior is already in main and the 1.5.7 bootstrap is replaced by the 2.0 Lobby bootstrap.
4. Keep #218 out of the release critical path; decide it as an optional follow-on, not a dependency for 2.0.

### Sprint 2 — produce a clean Lobby 2.0 PR series
5. Create a fresh feature branch from current main and port the existing #217 Lobby server/UI and tests without Bitcoin onboarding or broad entity-registry edits.
6. Add the official pinned bootstrap and per-platform launchers (Termux:Widget, XDG desktop, headless CLI). Default to an immutable stable tag for release installs.
7. Add generic Linux preflight and dependency preparation with explicit package plan/consent. Do not run the whole Lobby as root; request only narrowly scoped package-manager elevation when the user approves.
8. Implement the Lobby action that downloads and verifies the canonical Node Core installer package and then invokes only the approved installer/update entry points.
9. Complete opening, node health/status, repair, maintenance and rollback-safe update operations; prove storage, IPFS repo, configuration, identity and certificates remain intact.

### Sprint 3 — platform and release validation
10. Add Ubuntu 24.04 and Debian 13 plus Fedora supported version on x86_64; run aarch64 only where a real runner exists. Termux needs a physical ARM64 device acceptance run. Unknown Linux terminal apps may use the generic CLI profile only after its capability tests pass.
11. Add end-to-end scenarios: clean Lobby bootstrap, preflight, dependency consent, full core install with Kubo, certificate verification in core, open node, status, repair a controlled missing component, update and interrupted-update rollback, persistent data comparison.
12. Replace the old release workflow's v1.5.6 defaults and "exactly two installer/updater assets" contract. The 2.0 release should publish a pinned Lobby bootstrap, Lobby package/metadata, Core package, updater, checksum manifest, SBOM and provenance; every artifact must point to the same tagged source commit.
13. Update `VERSION`, changelog, compatibility manifest and install docs only after the RC code is ready. Run a clean-device RC rehearsal; then run the strict release readiness gate and publish `v2.0.0`.

## D. Required GitHub Actions contract

| Workflow | Trigger / scope | Required release evidence |
|---|---|---|
| PR validation | Every PR to main | Python/shell syntax, unit tests, manifest/repository contract |
| Lobby validation | Changes under Lobby/bootstrap/web | Server integration, loopback-only binding, auth/Origin/Host/CSRF controls, no arbitrary command execution, JS syntax |
| Linux preflight matrix | Compatibility/preflight changes | Ubuntu/Debian/Fedora package-manager detection and consent plan; no unintended system mutation |
| Installer E2E | Installer/bootstrap changes | Real clean install/update/uninstall and rollback, non-root |
| Kubo integration | Kubo/install/update changes | Local daemon/API, content add/cat, repo preservation and two-node transfer |
| Certificate acceptance | Certificate registry/trust changes | Signature/trust-anchor/expiry/revocation checks; negative cases; no auto-trust of catalog entries |
| Repair/update E2E | Lifecycle changes | Injected corruption, repair, restart, interrupted update and persistent-data hashes |
| Termux physical acceptance | Termux-specific release changes | Real ARM64 device; job must run, not skip |
| Release package | Tag/RC candidate | Bootstrap, Lobby, core and updater assets; SHA-256/SHA-512, SBOM and provenance |
| Strict release gate | RC/final tag only | Every acceptance boolean/evidence ref satisfied; reject skipped critical platform jobs |

### Check-state policy
- `success` means an executed check passed.
- `skipped` is not `success` for a required platform or acceptance case.
- `neutral`, `cancelled`, `timed_out`, `action_required`, `failure`, missing, queued or in-progress checks do not authorize merge/release.
- Every result must belong to the exact latest head SHA. After a merge, rerun required main checks on the new main SHA.
- The final release gate must run strict mode; the audit-only mode is useful for producing a blocker report but cannot authorize publication.

## E. Explicit release blockers

The following are release blockers until evidence exists:
1. Stable, production-pinned Lobby bootstrap (no feature branch default).
2. Lobby installation and service/launchers for each declared supported platform.
3. General Linux dependency preflight and consented package preparation.
4. Core package install through Lobby, including Kubo and persistent storage setup.
5. Verifiable installation of the actual core trust/certificate artifacts using existing issuer/trust material; do not invent a root CA.
6. Open, status, repair, update and rollback operations from Lobby.
7. Physical Termux ARM64 acceptance; all required device checks must execute.
8. Release packaging contract and strict publication workflow migrated from installer/updater v1.5.6 to Lobby bootstrap + managed core v2.0.
9. Clean-device RC acceptance and all required PRs merged with main green.

**Fastest path in one sentence:** merge the audited control PR, land the small P2P reliability patch, discard/supersede stale release work, then split and port the useful Lobby implementation into small main-based PRs with the missing Linux/core/certificate/lifecycle E2E gates; only after that publish v2.0.0.
