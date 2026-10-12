# Downloadable installer packages

The current repository versions are read directly from `VERSION` and `applications/hashpaper/VERSION`. The packaging workflow builds packages from the checked-out commit and publishes SHA-512 checksum files.

## Package types

- **Installer source package**: complete repository source, intended for a fresh installation on a supported platform.
- **Updater package**: the Node Core OS and HashPaper updater scripts for an existing installation only. It is not a fresh installer.

Packages can be downloaded from the successful **Package Node Core OS installers** workflow run under Actions. When a version tag such as `v1.2.9` is pushed, the workflow also attaches the archives and checksums to that GitHub Release.

## Important platform status

The package process does not itself establish platform compatibility. The current installer has CI coverage on Ubuntu GNU/Linux. A real Termux/Android installation has not been validated by this workflow, so do not treat the generated fresh-install archive as a verified Termux installer until device-level tests pass.

All installer and updater scripts must be run as the normal user. Root and `sudo` execution are forbidden. The updater is only for an existing installation and is designed to preserve user storage and Kubo/IPFS data.
