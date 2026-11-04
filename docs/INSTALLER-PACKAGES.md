# Downloadable Node Core OS installer packages

The package workflow reads the semantic version from `VERSION` and builds archives from the exact checked-out commit. Every archive is accompanied by a SHA-512 checksum file.

## Package types

- **Fresh-install source package**: Node Core OS source and installer files for a clean installation.
- **Existing-install updater package**: the protected updater plus the exact source archive and commit marker. It is for an existing installation and is not a fresh installer.

HashPaper and P2P Contracts are suspended and excluded from the installable Node Core OS package.

## Release tags and assets

The release workflow accepts both version tag forms: `vMAJOR.MINOR.PATCH` and `MAJOR.MINOR.PATCH`. The `VERSION` file must match the numeric version in the tag. Release publication attaches the source installer, updater, and their SHA-512 files to the GitHub Release.

The Actions artifact is a temporary workflow artifact; it is not a substitute for the downloadable assets attached to the Release.

## Verify and install

Download the installer archive and its matching checksum from the [official releases page](https://github.com/byLAEV/Node-Core-OS/releases), then verify it before extraction:

```bash
sha512sum --check node-core-os-installer-VERSION.tar.gz.sha512
tar -xzf node-core-os-installer-VERSION.tar.gz
cd node-core-os-installer-VERSION
```

For GNU/Linux, run `bash installer/install.sh`. For native Android Termux ARM64, run `bash installer/termux-install.sh` from inside Termux. Run every installation and update command as the normal user, never as root or with `sudo`.

## Platform and dependency boundaries

- The GNU/Linux package workflow currently builds the bundled Kubo archive for Ubuntu 24.04 x86_64. Other supported GNU/Linux architectures may download their matching Kubo release during installation.
- Python wheels in the package are built for the GNU/Linux packaging runner. They must not be installed into Termux/Android.
- Termux uses its native `python-cryptography` and `kubo` packages and a Python virtual environment that can access Termux system packages.
- Automated Termux tests run on GNU/Linux fixtures. They do not prove successful execution on a physical Android device; a real-device smoke test is still required.

A successful package build proves packaging and the tests that ran in CI. It does not, by itself, prove installation on every operating system, architecture, or Android device.
