# Node Core OS 1.5.6 — Debian ARM64 terminal package

This packaging target preserves the original terminal application. It does not introduce a GUI, web dashboard, replacement menu, or second implementation.

## Single implementation, two distribution methods

- Source distribution: from the original 1.5.6 source directory, run `python3 main.py`.
- Debian distribution: install this ARM64 package and run `node-core-os`.

Both launch the exact same `main.py`, `node_core/ui.py`, `node_core/bios.py`, runtime, storage, and Kubo/IPFS integration from the immutable source commit `08d994574775a0ec3d9dcc4b2e88862152d1ea3b` (tag `v1.5.6`).

## Build

On an ARM64 Debian-family build host with Git and dpkg-dev installed:

```sh
sudo apt-get install git dpkg-dev
git checkout terminal-deb-1.5.6
bash packaging/debian-terminal/build-deb.sh
```

The resulting package is written to `build/node-core-os_1.5.6-1_arm64.deb`.

The build script obtains the application payload from the pinned historical commit, not from the current branch's application files.

## Install and run

```sh
sudo apt install ./build/node-core-os_1.5.6-1_arm64.deb
node-core-os
```

Run the application as the normal user. Do not use `sudo node-core-os`. The launcher rejects root execution; the original runtime also enforces user-level operation.

## Data and upgrade policy

The package places immutable application code in `/usr/lib/node-core-os/1.5.6` and the launcher in `/usr/bin/node-core-os`. Runtime data remains in the invoking user's `$HOME/.node-core` directory, as defined by the original 1.5.6 configuration. The package contains no maintainer scripts that initialize, overwrite, or delete user data. Removing the Debian package removes the packaged code and launcher, not `$HOME/.node-core`.

## Runtime requirements and limits

- GNU/Linux ARM64 with a Debian-compatible dpkg package manager.
- Python 3.10 or newer.
- Kubo/IPFS is an independent executable. The original runtime detects and reports it; this package does not silently install Kubo or alter system services.
- The optional native P2P cryptographic functions require the original project's Python dependency `cryptography>=42.0.0`. Install a compatible package in the user's Python environment before using those functions.
- This ARM64 Debian package is not a Termux/Android package. LinDesk must be confirmed as a glibc-based Debian-compatible ARM64 system before installation.

## Validation

GitHub Actions builds on an ARM64 Ubuntu runner, checks the package metadata and payload, compiles the historical Python source, and runs the original unit-test suite. A successful package build is not, by itself, proof that every LinDesk image or optional Kubo/P2P feature is compatible.
