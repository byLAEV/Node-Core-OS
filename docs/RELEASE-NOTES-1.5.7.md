# Node Core OS byLAEV — 1.5.7 Release Notes

**Release candidate — pending CI and publication verification**

## One-command installation and updating
- Add `update.sh` at repository root as the simple public entry point.
- Download and validate the official source archive before invoking the unified installer.
- Existing installations delegate to the protected updater; fresh installations use the regular installer.
- Route the installed `node-core-update` command through the same bootstrap.

## Termux and compatibility
- Detect the Linux kernel independently from Python's reported platform name.
- Correctly classify Termux when Android Python reports `Android` while the kernel reports `Linux`.
- Fix the undefined package-manager variable that caused compatibility preflight to crash.
- Add regression tests for Android Python 3.13, Linux kernel and ARM64 Termux.

## Data protection
- Keep root and sudo forbidden.
- Preserve local storage, identity, configuration, Kubo executable and IPFS repository.
- Retain the protected updater's backup, verification and rollback model.

## Validation boundaries
- Automated Linux CI and real Termux-device testing are distinct.
- Do not infer physical Termux validation from Ubuntu CI.
- This candidate is not a published release until the exact tag, CI, two archives and embedded checksums are verified.