# Node Core OS Installer

The installer provides the first Linux installation path for Node Core OS.

## Requirements

- Linux
- Python 3.10+
- pip available through `python3 -m pip)

## Install

From the repository root:

```bash
./installer/install.sh
```

The installer:

1. validates Python;
2. installs the Node Core Python package for the current user;
3. creates `~/.node-core`;
4. initializes the Node Core runtime;
5. verifies the `node-core` launcher.

The installation is intentionally user-local and does not require root privileges.

## Start

```bash
node-core
```

If the command is not found, ensure `~/.local/bin` is in `PATH`.

## Uninstall

```bash
./installer/uninstall.sh
```

Uninstall removes the package and launcher but preserves `~/.node-core` so node data is not destroyed accidentally.

## Kubo

Kubo remains an external Node infrastructure dependency. The installer currently prepares the Node Core environment but does not silently download or replace a Kubo installation. Kubo lifecycle and configuration remain controlled by Node Core BIOS.

## Scope

This is Installer v1. Identity, reputation, protocols, services, applications, system-wide services, and automatic Kubo distribution are future installer/runtime work.
