# Node Core OS byLAEV

Node Core OS is a modular, local-first runtime for managing local data and decentralized storage through Kubo/IPFS.

## Release line

The restructuring branch starts the **1.6.0** line. The previous repository tree is preserved without rewriting its contents under [historial/](historial/). Historical code is reference material and is not automatically installed or executed.

## Supported targets

- **GNU/Linux ARM64 (Debian-family):** native Debian package `.deb`, architecture `arm64`.
- **Termux Android (AArch64):** separate Android/Bionic adapter and Termux-native packaging. A Debian ARM64 package built for glibc is not compatible with Termux.
- **Lindesk:** pending identification and validation of its distribution, libc, package manager, and architecture. No compatibility claim is made until CI or device tests pass.

## Quick start from source

```sh
python3 -m node_core_os --help
python3 -m node_core_os status
python3 -m node_core_os init
```

## Build Debian package

On Debian/Ubuntu ARM64 with Python 3 available:

```sh
./packaging/debian/build.sh
sudo apt install ./dist/node-core-os_1.6.0_arm64.deb
```

The package installs a Python CLI and creates user data under `~/.local/share/node-core-os`. It does not install, start, or configure Kubo automatically.

## Design rules

- Preserve user data across upgrades and uninstall operations.
- Never publish local files to IPFS without an explicit user action.
- Keep platform-specific paths and dependencies in adapters.
- Treat CIDs as content identifiers, not proof of identity or permanence.
- Mark features as verified only after automated and target-device tests pass.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/PLATFORM-MATRIX.md](docs/PLATFORM-MATRIX.md), and [docs/RELEASE.md](docs/RELEASE.md).
