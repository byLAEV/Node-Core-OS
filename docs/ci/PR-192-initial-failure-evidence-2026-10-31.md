# PR #192 — initial CI failure evidence

- Evidence captured: 2026-10-31
- Pull request: https://github.com/byLAEV/Node-Core-OS/pull/192
- Tested head before corrections: `b2bcb46fb2bb3d0f06fc8bde32527a3ac0d3a476`
- Execution mode: GitHub-hosted Ubuntu 24.04; product/test jobs verified an ordinary non-root user before running.
- Privilege policy: no product installation or product test step used `sudo` or root. Docker image/network preparation was performed by the hosted CI orchestration context; containers ran as UID 1001.

## Failures observed

| Workflow | Run ID | Job ID | Result | Failure |
|---|---:|---:|---|---|
| Independent Network Domains | 41190796397 | 124507016068 | failure | 2 unittest errors caused by missing `threading` import in `node_core/web_ui.py`. 408 tests ran; 2 errors, 1 skipped. |
| GNU/Linux Terminal CI | 41190135497 | 124505043173 | failure | Same two `threading` NameErrors in the web service/background sync tests. |
| Installer E2E | 41190135508 | 124505043053, 124505043155 | failure | Both no-user-systemd and user-systemd lifecycle variants installed and launched Node Core successfully; updater verification then ran the test suite and failed on the same two `threading` NameErrors. The updater rollback restored the application and commit marker; Kubo/IPFS and persistent data were not modified. |
| Three-distro native P2P E2E | 41190135533 | 124505043129 | failure | Docker `inspect --format` template failed: `template parsing error: template: :1: bad character U+002D '-'`. Failure occurred while creating/inspecting the isolated network, before installation or P2P tests; subsequent steps were skipped. |

## Relevant log excerpts

- Web failure: `NameError: name 'threading' is not defined` at `NodeCoreWebServer.start_background_sync()`, line 102 of `node_core/web_ui.py`.
- Web service startup failure was a downstream consequence of the same missing import.
- P2P failure: `template parsing error: template: :1: bad character U+002D '-'` while addressing Docker network `node-core-p2p` in a Go template expression.

## Original run links

- [Independent Network Domains — run 41190796397](https://github.com/byLAEV/Node-Core-OS/actions/runs/41190796397)
- [GNU/Linux Terminal CI — run 41190135497](https://github.com/byLAEV/Node-Core-OS/actions/runs/41190135497)
- [Installer E2E — run 41190135508](https://github.com/byLAEV/Node-Core-OS/actions/runs/41190135508)
- [Three-distro native P2P E2E — run 41190135533](https://github.com/byLAEV/Node-Core-OS/actions/runs/41190135533)

## Preserved GitHub artifact

The Independent Network Domains run uploaded diagnostic artifact `network-domain-validation-41190796397` (artifact ID `13038583382`, SHA-256 `19ae3660466ddf7e154f34ce9809c8516dd1abbedcc6e4407e52be58b5760817`, expiry 2026-11-14). The other failed jobs did not publish artifacts; their job logs remain accessible from the run pages above.

## Corrections committed to the PR branch

1. `node_core/web_ui.py`: imported the standard-library `threading` module used by the existing background sync implementation.
2. `.github/workflows/three-distro-native-p2p-e2e.yml`: changed all four Docker network address template expressions to use Go's `index` function for the hyphenated network key `node-core-p2p`.

The corrected commits are recorded in the PR branch history. Re-run results must be assessed separately; this document records the original failures and does not claim the corrected tests passed.
