# Release and migration policy

## Version 1.6.0

This branch establishes a clean product baseline. It does not claim feature parity with the archived repository.

## Historical preservation

The original root tree is retained under `historial/` with paths and blob contents preserved. Historical workflows are not active from their archived location. New workflows must be added under `.github/workflows/`.

## Release gates

1. Unit tests pass.
2. Debian package builds on ARM64.
3. Package metadata and file ownership are inspected.
4. Install, upgrade, and uninstall tests pass in a disposable Debian ARM64 environment.
5. Termux packaging is built and tested on an actual Termux AArch64 environment.
6. Lindesk is added only after its platform identity and tests are available.
7. Checksums and release artifacts are published with the source commit recorded.

Uninstall must not remove the user's data directory.
