# Node Core OS — Dependencies

## Platform contract

Node Core OS is an **GNU/Linux terminal-only** project.

The official repository, installer, runtime, CI, and documentation do not target Windows, macOS, Android, mobile runtimes, or graphical interfaces.

Termux is not an official target. Restrictions observed in Linux-like terminal environments are used only as architectural constraints so the installer does not unnecessarily depend on root, sudo, systemd, privileged mounts, or fixed system paths.

## Dependency classes

| Dependency | Class | Required | Used by | Detection / verification |
|---|---|---:|---|---|
| GNU/Linux | Platform | Yes | Installer/runtime | `uname -s` = `Linux` |
| Bash | Installer shell | Yes | `installer/*.sh` | `bash --version` |
| Python 3.10+ | Runtime | Yes | Node Core | `python3 --version` |
| Python standard library | Runtime | Yes | Node Core | Python import/compile tests |
| Kubo | Infrastructure | Yes for IPFS features | `KuboManager` | `ipfs version` + API health |
| curl or wget | Installer utility | Yes, one of them | Kubo acquisition | command detection |
| tar | Installer utility | Yes | Kubo archive extraction | command detection |
| sha512sum | Installer verification | Yes | Kubo archive verification | command detection |
| core POSIX utilities | Installer/runtime | Yes | filesystem/process operations | individual command checks |
| Git | Development | No for installed runtime | contributors/CI workflows | development environment |
| unittest | Development/runtime tests | Yes for repository tests | `tests/` | Python standard library |
| systemd --user or another service supervisor | Service integration | Optional | future managed services | supervisor-specific detection |

## Python dependencies

The current Node Core runtime intentionally uses only the Python standard library.

`requirements.txt` therefore contains no third-party Python packages.

This is deliberate: the installer should not create a Python package dependency chain unless a real runtime requirement is introduced.

## Kubo

Kubo is an external infrastructure dependency. Node Core OS does not reimplement IPFS.

The installer pins a known Kubo release rather than installing an unversioned "latest" binary. The current installer baseline is **Kubo v0.43.1**.

Official Kubo distributions provide Linux AMD64, ARM64 and RISC-V binaries. The first installer implementation supports Linux AMD64 and ARM64; unsupported architectures stop with an explicit message rather than silently installing the wrong binary.

Kubo distribution source:

- https://dist.ipfs.tech/kubo/
- https://github.com/ipfs/kubo/releases

The installer downloads the archive and its published SHA-512 checksum, verifies the archive, and only then installs the binary.

## Filesystem model

Node Core uses a user-owned data root:

`~/.node-core/`

The installer does not require a system-wide `/usr/local`, `/etc`, or `/var/lib` installation for Node Core data.

The expected layout is:

```
~/.node-core/
├── app/          # installed Node Core source
├── bin/          # node-core launcher and Kubo executable
├── storage/      # local Node Core storage
├── registry/     # future top-level registries
├── ipfs/         # Kubo repository
├── logs/         # runtime/service logs
├── runtime/      # runtime state
├── services/     # service metadata
├── identity/     # future identity state
└── config.json
```

The runtime currently creates only the directories it actually needs. The complete layout is an architectural target, not a promise that every directory is populated on first boot.

## Network requirements

The local runtime does not require Internet access to create a CID from content already available to Kubo or to operate local storage.

Internet/network connectivity is required for operations that retrieve content from remote peers or otherwise communicate outside the local node.

The installer requires network access only when Kubo must be downloaded.

## Privileges

The installer is designed to operate without root privileges for the Node Core user-owned installation.

No feature should assume `sudo` is always available.

A Linux service supervisor may require its own platform-specific permissions, but that is a service integration concern and not a prerequisite for the Node Core runtime.

## Dependency policy

1. Every new external dependency must be documented here.
2. Runtime dependencies and installer-only utilities must remain separate.
3. Python third-party packages require an explicit architectural reason.
4. Platform-specific dependencies must not become hidden official platform targets.
5. The installer must fail clearly when a mandatory dependency is missing.
6. CI must validate the same dependency assumptions used by the installer.
