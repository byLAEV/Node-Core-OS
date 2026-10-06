# Node Core OS Installer

> **Installer v1 targets Linux terminals only.**

Node Core OS is installed as a user-local Node infrastructure layer on an existing Linux system.

## Supported target

- Linux terminal
- x86_64 / amd64
- aarch64 / arm64
- riscv64
- Python 3.10 or newer

Android, Termux, Windows, macOS, and GUI-only environments are outside the scope of Installer v1.

## Installation

From the repository root:

```bash
./installer/install.sh
```

The installer:
1. verifies the host is Linux;
2. rejects Android/Termux environments;
3. detects the CPU architecture;
4. verifies Python 3.10+;
5. creates ~/.node-core;
6. installs a private Python runtime;
7. copies the Node Core runtime into the installed Node;
8. detects an existing Kubo installation;
9. installs the pinned official Kubo release when Kubo is absent;
10. verifies the Kubo archive with SHA-256;
11. initializes the Kubo repository;
12. creates the node-core launcher in ~/.local/bin;
13. verifies the resulting Node environment.

The installer does not require root privileges.

## Installed layout

```text
~/.node-core/
├── app/
├── bin/
├── ipfs/
├── storage/
├── venv/
└── config.json

~/.local/bin/
└── node-core
```

The local storage and Kubo repository remain separate.

## Kubo

Installer v1 uses the official Kubo v0.43.1 Linux release when it needs to install Kubo.

The release artifacts are pinned by architecture and verified by SHA-256 before extraction.

Kubo remains an external infrastructure component. Node Core manages its configured executable and repository but does not reimplement IPFS.

## Uninstall

```bash
./installer/uninstall.sh
```

The uninstaller removes the Node Core runtime, private Python environment, launcher, and Node-managed Kubo binary while preserving ~/.node-core/ipfs, ~/.node-core/storage, and configuration data.

## Verification

Static and unit verification:

```bash
./installer/test.sh
```

Installer v1 is considered complete only after the installer itself has been executed successfully on a real Linux environment.