# Development

## Supported development environments

Node Core OS is a Linux-terminal application. GNU/Linux is the primary development and CI environment. Native Termux on Android ARM64 is a compatible runtime environment with a platform-specific dependency path inside the same installer. Windows and macOS are not supported targets.

## Runtime and dependencies

- Python 3.10 or newer.
- CI currently runs the core suite on Python 3.12.
- Install the repository's declared runtime dependency before running the application or tests:

```bash
python3 -m pip install -r requirements.txt
```

The installed product uses `~/.node-core/runtime/node-core-venv/bin/python`. Tests against an installed node must use that interpreter, not an unrelated system Python.

## Run from a development checkout

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

## Test

```bash
python3 -m unittest discover -s tests -v
bash installer/tests/syntax.sh
bash installer/tests/manifest.sh
bash installer/tests/update-preservation.sh
bash installer/tests/termux-installer.sh
```

CI validates GNU/Linux on Ubuntu 24.04 with Python 3.12, including shell syntax, installer regression fixtures and the Python test suite. A CI fixture that simulates Termux selection is not equivalent to a physical Android-device test.

## Installer and updater

Use the one canonical entry point:

```bash
bash installer/install.sh
```

It detects GNU/Linux versus native Termux and selects the matching dependency path. `bash installer/termux-install.sh` is a backwards-compatible alias only. Do not create a second platform-specific product or installer.

All product installation, update and test commands must run as an ordinary user, never as root or with `sudo`. See [Installer Specification](INSTALLER.md), [Dependency Contract](DEPENDENCIES.md), and [Repository Coherence Contract](REPOSITORY-COHERENCE.md).

## Milestones

1. Maintain the runtime, installer and lifecycle.
2. Preserve local storage and Kubo/IPFS boundaries.
3. Maintain persistent technical node identity and cryptographic controls.
4. Keep declared personal identity separate from verified claims.
5. Implement and test public API contracts before calling them supported.
6. Verify node-to-node authentication, authorization, discovery and transport separately.
7. Develop evidence, provenance, corroboration and consensus with explicit acceptance criteria.
8. Keep proposals, suspended components and active runtime capabilities clearly distinguished.
