# Node Core OS 1.5.7 — Release Checklist

**Status:** release candidate; publication blocked pending CI and release verification.
**Version:** 1.5.7
**Repository:** byLAEV/Node-Core-OS

## Release scope
- Public one-command entry point: `bash update.sh`.
- Bootstrap downloads the official repository snapshot, validates the TAR archive and version, and delegates to the unified installer.
- Existing installations are delegated to the protected updater with application backup, candidate validation and rollback.
- Termux detection uses Linux kernel identity plus `TERMUX_VERSION` and `PREFIX`, supporting Android Python builds that report `platform.system() == "Android"`.
- Fix compatibility detector's undefined package-manager variable.
- Installed `node-core-update` command routes through the unified bootstrap.
- Preserve local storage, identity material, configuration, Kubo binary and IPFS repository.

## Required verification before publication
1. Run compatibility unit tests, repository coherence tests, Python compilation and all shell syntax tests.
2. Run GNU/Linux install/update/rollback E2E on Ubuntu, Debian and Fedora as a normal user.
3. Run package build and offline updater E2E.
4. Inspect the actual Termux device installation on Android ARM64; Linux CI is not a substitute.
5. Verify the root bootstrap can update an existing installation and can install a fresh one.
6. Verify `node-core-update` uses the bootstrap after installation.
7. Confirm persistent data and IPFS repository hashes are unchanged by an update.
8. Create tag `v1.5.7` on the exact approved commit and publish exactly two archives through `bios-release-packages.yml`.
9. Verify both archives, their SHA-256/SHA-512 digests, embedded source commit and release assets.

## User command
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/byLAEV/Node-Core-OS/main/update.sh)
```

Run as the ordinary installation user. Never use root or sudo.

## Release decision
Do not publish until all required automated checks pass and physical Termux validation is reported honestly.