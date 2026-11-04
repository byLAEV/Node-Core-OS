# Node Core OS — Dependency Contract

**Contract version:** 1.5.6  
**Machine-readable contract:** [REPOSITORY-CONTRACT.json](REPOSITORY-CONTRACT.json)  
**Canonical installer:** `bash installer/install.sh`

This document describes dependencies required by executable code and installer behavior in this repository revision.

## Supported environments

| Environment | Status | Dependency strategy |
|---|---|---|
| GNU/Linux x86_64 | Primary target | User-owned Python virtual environment; pinned Linux Kubo binary |
| GNU/Linux aarch64 | Supported installer target | User-owned Python virtual environment; matching pinned Linux Kubo binary |
| Termux Android aarch64 | Compatible terminal target | Same installer; Termux-native packages through `pkg`; native Python site-packages |
| Other Linux architectures | Not supported by current installer | Fail closed; never substitute another architecture's binary |
| Windows / macOS | Not supported | No compatibility claim |

Termux compatibility is implemented inside the shared Linux-terminal installer. `installer/termux-install.sh` is a compatibility alias, not a second installer. The Node Core Terminal Compatibility Layer (NCTCL) evaluates declared capabilities rather than requiring a fixed terminal-emulator or distribution-name allowlist. See [TERMINAL-COMPATIBILITY.md](TERMINAL-COMPATIBILITY.md).

## Required runtime dependencies

| Dependency | Scope | Requirement | Evidence / verification |
|---|---|---|---|
| Python | Core runtime | 3.10 or newer | Installer version check; CI currently tests Python 3.12 |
| `cryptography` | Core runtime | `>=42.0.0` | `requirements.txt`; used by node identity, certificates, TLS, signed policy and secure messaging |
| Python standard library | Core runtime | Included with Python | HTTP uses `urllib`; JSON, hashing, filesystem, sockets and process handling use standard modules |
| Kubo / IPFS | Infrastructure | Required for IPFS/Kubo features | GNU/Linux pinned v0.43.1; Termux native `kubo` package |
| Bash | Installer | Required | Installer scripts and shell tests |
| curl or wget | Installer/updater | At least one | Downloads and API operations |
| tar | Installer | Required | Archive extraction |
| sha512sum | Installer | Required | Kubo archive integrity verification |
| Linux utilities | Installer | Required | `awk`, `find`, `grep`, `sed`, `stat`, `realpath`, `mktemp` and core file/process utilities |

The Node Core Python runtime currently has one declared third-party distribution: `cryptography`. The code uses standard-library `urllib`, not third-party `requests`. Do not add dependencies based on generic references to HTTP requests; add them only when executable imports require them.

## Python environment

The installed application runs with `~/.node-core/runtime/node-core-venv/bin/python`.

GNU/Linux installs requirements into this private virtual environment, using compatible binary wheels only, preferring bundled wheels and then the configured Python package index. Source compilation is not an automatic fallback. Install, verification, update candidate validation and CI use the shared `node_core.security.crypto_health` self-test for version, Ed25519 sign/verify/tamper rejection, PKCS8 PEM round-trip and SHA-256.

Native Termux uses its Android-native `python-cryptography` package. Its virtual environment exposes Termux site-packages; GNU/Linux manylinux wheels must not be installed into Android Python.

Application compilation, tests and updater recovery validation must use the same private interpreter as the installed application. A system `python3` test is not evidence that the installed runtime environment is healthy.

Recovery checks dependencies against the recovered application's own `requirements.txt`. The Ed25519 smoke test is required when that manifest declares `cryptography`; legacy installations without that declaration are still checked using their own interpreter, compilation and test suite. They are not rejected merely because a later release introduced a dependency. Candidate releases install and verify all dependencies they declare before activation.

## GitHub Actions runtime

The core GNU/Linux CI workflow uses `actions/checkout@v5` and `actions/setup-python@v6`, which run on the GitHub Actions Node.js 24 runtime. This is separate from the Node Core application runtime: the product still requires Python 3.10 or newer and does not require global Node.js. These actions require Actions Runner 2.327.1 or newer; GitHub-hosted Ubuntu runners meet that baseline.

## Cryptographic capabilities and limits

The current code uses `cryptography` for persistent Ed25519 technical node identity and cryptographic functions in certificate, TLS, signed-policy and secure-messaging modules. The exact availability and verification status of each feature must be reported separately.

A technical node key proves control of that key, not a person's civil identity, uniqueness, legal status or trustworthiness. The technical private key is stored as a PEM file protected by filesystem permissions; the current identity store does not encrypt it at rest.

See [Cryptographic Runtime Contract and Recovery](CRYPTOGRAPHY-OPERATIONS.md) for platform-specific installation and failure recovery.

## Installer-only and optional dependencies

- Git is used for development and repository operations, not by the installed runtime.
- `systemd --user` is optional service integration. Kubo can use the Node Core-managed manual lifecycle when unavailable.
- Termux `pkg` is used only after native Termux detection to install missing user-space packages. GNU/Linux package managers are not invoked.
- OpenTimestamps tooling and HashPaper source are separate/optional paths, not Node Core core-runtime Python requirements in the 1.5.6 installed application. The installer removes the suspended HashPaper application source from the installed application tree.

## Kubo version and integrity

GNU/Linux installation pins Kubo v0.43.1 and verifies the archive against its published SHA-512 checksum before installation. Native Termux uses the Android-native `kubo` package from the configured Termux repository.

Kubo remains an external service and owns its repository, daemon, API, gateway, peer identity, content addressing and pinning. Node Core OS manages it through its adapter and user-level lifecycle.

## Privileges and host packages

Installer, updater and uninstaller reject UID 0. Do not use `root`, `sudo` or `su` for Node Core OS installation, update, tests or runtime operation.

On GNU/Linux, missing host utilities are reported; the installer does not invoke apt, dnf, yum, pacman, zypper or another system package manager. Native Termux is the explicit exception and may use `pkg install -y` for missing user-space packages.

## Change policy

1. Executable imports and runtime paths determine actual dependencies.
2. Every new third-party runtime dependency must be added to `requirements.txt` and this document.
3. Platform-native packages must be documented separately from pip distributions.
4. Installer-only tools must not be described as application runtime libraries.
5. CI, installer verification and updater recovery must use the same runtime dependency contract.
6. The repository coherence regression test must fail when `VERSION`, this contract, `requirements.txt`, installer defaults or platform behavior drift.
