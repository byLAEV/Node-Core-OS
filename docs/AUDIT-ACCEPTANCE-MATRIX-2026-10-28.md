# Node Core OS byLAEV — Audit Acceptance Matrix

Date: 2026-10-28 (UTC)
Audit branch: `maintenance/suspend-hashpaper-p2p-contracts-verified`
Base branch: `main`
Main SHA observed at audit start: `c74a53e3b36cb9cf5995f9ba7474c1a658cefdfd`
Audit branch SHA before this document and workflow-comment cleanup: `56ede0bd8479cb6e976f5e29450b33616257bfb6`
Pull request: [#188](https://github.com/byLAEV/Node-Core-OS/pull/188) — open, not merged at time of audit.

## Status definitions

- **PASS (observed):** a linked CI run completed successfully for the cited commit.
- **SKIPPED (intentional):** the suspended job did not run; this does not prove the source is safe in every other entry point.
- **OPEN:** evidence is incomplete or needs to be rerun against the latest audit commit.
- **NOT AUDITED:** no exhaustive inspection has yet been performed.

## Acceptance matrix

| ID | Area | Acceptance criterion | Evidence / current finding | Status | Regression test / next action |
|---|---|---|---|---|---|
| WF-01 | Suspended P2P workflows | P2P Contracts E2E jobs are not executed by PR CI | Runs [40641629946](https://github.com/byLAEV/Node-Core-OS/actions/runs/40641629946) and [40641629656](https://github.com/byLAEV/Node-Core-OS/actions/runs/40641629656) are skipped | PASS (observed) | Recheck all workflow entry points and dispatch paths after latest commit |
| WF-02 | Suspended HashPaper workflows | HashPaper jobs do not execute | Both workflow files retain their triggers but their jobs have `if: false`; job-level condition prevents execution | PASS (configuration inspected; runtime evidence pending) | Confirm checks show skipped; scan all workflows and packaging paths |
| WF-03 | Duplicate workflow conditions/comments | No contradictory or duplicate suspension logic | Removed duplicate suspension comment in `.github/workflows/three-independent-ubuntu-p2p-e2e.yml`; removed earlier duplicate condition/comment during prior fixes | OPEN | Validate YAML and rerun CI on latest commit |
| WF-04 | Privilege boundaries | Installer/updater tests reject root and do not use sudo | `installer/install.sh`, `installer/update.sh`, and `installer/lib/verify.sh` contain explicit root refusal; E2E has a static sudo/privileged-command check | PASS (source inspected; full cross-workflow scan pending) | Run non-root tests and scan every workflow/script for privileged commands |
| PKG-01 | Downloadable package exclusion | Installable archive excludes HashPaper and P2P Contracts application code and related workflows/docs | `.github/workflows/package-installers.yml` removes both application trees and selected related assets, then scans archive listing; error message now names both suspended apps | PASS (source inspected; package CI passed before latest installer changes) | Inspect archive manifest from latest SHA and fail if suspended paths occur |
| UPD-01 | Valid update | Validate source, run core tests, exclude suspended code/artifacts, and write exact commit marker only after validation | `installer/update.sh` backs up app and marker; validates version, compileall and unittest before writing marker; now removes P2P docs/workflows and OpenTimestamps helper from installed app | OPEN (new changes awaiting CI) | Run Ubuntu E2E and terminal/Termux update-preservation tests, including P2P artifact assertions |
| UPD-02 | Failed update rollback | Invalid download/archive or failed validation restores prior app and marker | Existing update-preservation test covers failure paths and checks prior marker/data | PASS (prior CI evidence; latest commit needs rerun) | Inject download, archive, validation and marker-write failures; verify rollback artifacts |
| DATA-01 | Kubo/IPFS and local data | Update does not replace Kubo executable, IPFS repository, config or user storage | Updater documents this boundary; preservation scripts check sentinel files; successful Kubo CI [40641630055](https://github.com/byLAEV/Node-Core-OS/actions/runs/40641630055) | PASS (prior CI evidence; latest commit needs rerun) | Hash before/after each success and failure scenario; check Termux config migration separately |
| CORE-01 | Core unit suite | All core tests run from extracted release before activation | Updater calls `python -m unittest discover -s tests -v`; release fixtures create importable `tests` package | OPEN (new changes awaiting CI) | Include missing tests directory and failing test as negative fixtures |
| MOD-01 | Local storage | Relative paths cannot escape configured storage root | `node_core/storage.py` resolves paths and rejects candidates outside root | PASS (source inspected) | Add tests for `../`, absolute paths, symlinks and path-race limitations |
| MOD-02 | Kubo integration | CLI/RPC operations use bounded timeouts and preserve user-owned repo | `node_core/ipfs.py` uses subprocess argument arrays and RPC timeouts; updater has explicit Kubo/data preservation boundary | OPEN | Review API binding trust, daemon lifecycle, process ownership and destructive operations |
| MOD-03 | Node identity certificates | Signature, issuer binding, time bounds, profile and revocation are checked | `node_core/security/node_identity_certificate.py` implements Ed25519/JWS checks; comments state revocation freshness is caller responsibility | OPEN | Verify negative tests, trust distribution and stale/missing revocation data behavior |
| BR-01 | Branch divergence | Every branch classified against `main` for ahead/behind, conflicting changes and unique fixes | First sample: maintenance branch is diverged (5 commits ahead, 26 behind at the comparison snapshot); several sampled legacy branches are fully behind | OPEN | Continue paginated inventory and compare each branch; do not merge branches automatically |
| MOD-04 | Full module audit | Identity, networking, certificates, storage, UI, dependency and runtime modules have evidence-based findings | Partial source inspection only; complete module-by-module test mapping not yet done | NOT AUDITED | Map each module to tests, dependencies, entry points and risk findings |

## Confirmed code observations

1. The maintenance branch was not merged into `main` during this audit.
2. The installable package build removes the suspended application trees from the staging directory rather than deleting them from Git history.
3. Installer/updater code removes suspended application code from the installed application tree; separate user data under the data directory is handled separately and preservation fixtures check it.
4. HashPaper and P2P workflow files can retain manual or path triggers while their jobs are disabled. This is not an execution path while the job-level `if: false` remains, but it requires a repository-wide check for alternate workflows, scripts and package manifests.
5. The successful CI evidence cited above belongs to commit `56ede0bd8479cb6e976f5e29450b33616257bfb6`. The later workflow-comment cleanup changes the branch SHA, so a new CI run is required before treating the latest revision as accepted.


## Findings added during the detailed audit

- **SUSP-01 — Partial suspension boundary in installed application (HIGH, corrected; CI pending).** Fresh install and update removed the two application directories and HashPaper artifacts but did not remove all P2P Contracts documentation/workflow artifacts and the OpenTimestamps helper. The package builder already excluded these paths. Aligned `installer/install.sh` and `installer/update.sh` with the package exclusion list and extended Ubuntu E2E plus offline updater/Termux fixtures to assert the application, selected docs, workflows and helper are absent after install/update. User-owned data under `$NODE_CORE_DATA_DIR/hashpaper`, Kubo/IPFS and local storage must remain untouched.
- **WF-04 — Duplicate comment in suspended P2P workflow (LOW, corrected; CI pending).** Removed the repeated suspension comment in `.github/workflows/three-independent-ubuntu-p2p-e2e.yml`.
- **MOD-05 — Kubo subprocess timeout (MEDIUM, open).** `node_core/ipfs.py::_run` invokes Kubo CLI with `check=True` but no timeout. A stalled CLI can block the UI/runtime indefinitely. Add bounded, operation-appropriate timeouts and tests; avoid a blanket timeout for commands that intentionally transfer large content.
- **MOD-06 — Kubo RPC endpoint trust boundary (MEDIUM, open).** `NodeConfig.load` accepts a configured `ipfs_api` URL without validating scheme/host. Because RPC calls are POST requests, a malicious or accidental remote endpoint could receive requests intended for the local Kubo API. Decide and enforce a policy (loopback-only by default, explicit opt-in for remote endpoints) and add tests for localhost, IPv4/IPv6 loopback, non-loopback and malformed URLs.
- **MOD-07 — Storage path race (LOW/MEDIUM, open).** `StorageManager.path` resolves and checks containment, which blocks ordinary traversal and existing symlink escapes, but subsequent open/write/delete operations are susceptible to a filesystem race if another same-user process changes a symlink between validation and use. Document the same-user threat boundary and consider directory-FD/no-follow APIs where supported.
- **MOD-08 — Default HashPaper data directory creation (LOW, open).** `NodeConfig.ensure_directories` still creates HashPaper-specific data directories on core boot. This does not execute the suspended app and must not be confused with deleting user data, but it may be inconsistent with a strict suspension policy. Decide whether to stop creating new empty directories while preserving all existing user data, then test migration behavior.

## Merge gate

Do **not** merge into `main` until all of the following are true:

- Required checks pass on the exact latest PR head SHA.
- The full workflow inventory proves suspended applications cannot be run or shipped through any workflow, installer, updater or package path.
- Ubuntu and Termux success/failure update tests pass without root or sudo.
- Kubo/IPFS executable, repository, configuration and user data are checked before/after successful update and rollback.
- Branch divergence has been classified; unique fixes are cherry-picked or merged only after review.
- Module-level findings have a regression test and a recorded result; unresolved risks are explicitly accepted rather than marked as passed.
