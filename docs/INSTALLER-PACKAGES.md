# Downloadable Node Core OS installer packages

The package workflow reads the Node Core OS semantic version from the repository `VERSION` file and builds packages from the exact checked-out commit. Each archive has a SHA-512 checksum file.

## Package types

- **Fresh-install source package**: Node Core OS source and installer files for a clean installation on the supported platform.
- **Existing-install updater package**: only the Node Core OS updater script and its README. It is for an existing installation and is not a fresh installer.

HashPaper is maintained as a separate application. The Node Core OS updater package does not include a HashPaper updater, and the Node Core OS version does not depend on the HashPaper version.

## Download and release

The package workflow uploads archives and checksum files as GitHub Actions artifacts. When a version tag such as `v1.5.2` is pushed, the workflow also attaches the archives and checksums to that GitHub Release.

Verify the downloaded archive before use:

```bash
sha512sum --check node-core-os-installer-1.5.2.tar.gz.sha512
```

Run installation and update scripts as the normal user, never as root or with `sudo`.

## Supported platform status

Automated real-install coverage targets Ubuntu 24.04 x86_64 GNU/Linux. Package creation does not by itself establish compatibility with other platforms. Termux/Android has not been validated by this workflow and is not declared supported by this release.
