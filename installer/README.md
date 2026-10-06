# Node Core OS Installer

The installer provides the first Linux installation path for Node Core OS.

## Requirements

- Linux
- Python 3.10+
- Python's standard `venv` module.

## Install

From the repository root:

```bash
./installer/install.sh
```

The installer:

1. validates that the host is Linux;
2. validates Python 3.10+;
3. creates an isolated Python environment at `~/.node-core/venv`;
4. installs the Node Core package into that environment;
5. creates the `node-core` launcher at `~/.local/bin/node-core`;
6. initializes and verifies the Node Core runtime.

The installation is user-local and does not require root privileges.

## Start

```bash
node-core
```

If the command is not found, ensure `~/.local/bin` is in `PATH`.

## Uninstall

```bash
./installer/uninstall.sh
```

Uninstall removes the Node Core Python environment and launcher but preserves `~/.node-core` data.

## Kubo

Kubo remains an external Node infrastructure dependency. Installer v1 does not silently download, replace, or manage a Kubo installation. Kubo lifecycle and configuration remain controlled by Node Core BIOS.

## Scope

Installer v1 establishes the Linux installation boundary. Identity, reputation, protocols, services, applications, system-wide services, and automatic Kubo distribution remain later stages.
