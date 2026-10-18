# Node Core OS 1.5.2 on Termux (Android)

This is the direct Termux installation path. It does not install Debian, Ubuntu, PRoot, or another Linux distribution.

## Requirements

- The official Termux app with its package repositories working.
- Android ARM64/aarch64.
- A normal Termux user session; do not run as root.
- Network access to the Termux package repository and GitHub.

## Install from the versioned source archive

Use a published source installer archive that includes `installer/termux-install.sh`. The original v1.5.2 release archive predates this Termux wrapper, so it must not be assumed to contain it. After a package including this change is published, download its archive and matching SHA-512 file from the [official releases page](https://github.com/byLAEV/Node-Core-OS/releases). From the directory containing both files, verify the checksum path as follows:

```bash
mkdir -p dist
ln -sf ../node-core-os-installer-1.5.2.tar.gz dist/node-core-os-installer-1.5.2.tar.gz
sha512sum -c node-core-os-installer-1.5.2.tar.gz.sha512
tar -tzf node-core-os-installer-1.5.2.tar.gz >/dev/null
tar -xzf node-core-os-installer-1.5.2.tar.gz
cd node-core-os-installer-1.5.2
bash installer/termux-install.sh
```

The Termux wrapper checks the platform and required commands. It installs only missing Termux packages with `pkg`, including `kubo` if the `ipfs` executable is not already available, then invokes the regular installer. Kubo runs from Termux's Android-native package at `$PREFIX/bin/ipfs`; the GNU/Linux Kubo archive is not used.

## Existing installation safety

The wrapper never overwrites an existing application to perform a fresh install. If it detects an existing Node Core OS installation, it delegates to the existing updater, which asks for confirmation before applying an update. If it detects persistent Node Core/IPFS data without a complete application, it stops and asks for manual review rather than replacing configuration or data.

The updater replaces application code only. It preserves `~/.node-core/storage/`, `~/.node-core/ipfs/`, `~/.node-core/config.json`, and the existing Termux Kubo executable.

## Start Node Core OS

After a successful new installation:

```bash
"$HOME/.node-core/bin/node-core"
```

To make the launcher available in the current shell:

```bash
export PATH="$HOME/.node-core/bin:$PATH"
```

Automated shell checks and Termux-specific preservation tests cover the wrapper and updater. A successful CI run on GNU/Linux is not a substitute for a real-device smoke test on Android; report any device-specific failure with the command output and the Kubo log at `~/.node-core/logs/kubo.log`.
