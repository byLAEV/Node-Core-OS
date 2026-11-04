# Node Core OS — Linux terminal compatibility: Termux

Node Core OS is a terminal-first Linux application. Termux on Android is one compatible Linux terminal environment; it is not a separate Node Core OS product or a separate installation implementation.

## One installation command

Inside a current Termux session, as the normal Termux user:

```bash
bash installer/install.sh
```

Use this exact same entry point on GNU/Linux distributions. The installer detects native Termux and selects compatible Android-native dependencies automatically. Debian, Ubuntu, PRoot, root, and sudo are not required.

The old command `bash installer/termux-install.sh` remains available only as a backward-compatible alias. It forwards to the unified installer.

## Environment-specific dependency selection

- GNU/Linux distributions: the installer checks required host commands, prepares a private Python environment, and installs the matching pinned GNU/Linux Kubo binary.
- Native Termux: the installer uses `pkg` only to install missing user-space packages, including Termux-native Python cryptography and Kubo. It does not install glibc manylinux wheels or GNU/Linux Kubo binaries into Android.
- Both environments use the same Node Core application, `~/.node-core` data layout, identity initialization, launcher, verification contract, and updater.

Every command must run as the normal user. Never run installation, update, or uninstallation with root or sudo.

## Existing installation and recovery

The unified installer delegates an existing installation to the updater; it must not overwrite the application as a fresh installation. The updater preserves:

- `~/.node-core/storage/`
- `~/.node-core/ipfs/`
- `~/.node-core/config.json`, except for a required migration of the Kubo executable path to the Termux-native executable
- Termux's existing Kubo executable at `$PREFIX/bin/ipfs`

If the updater reports pending recovery files under `~/.node-core/runtime/update`, stop. Do not delete or rename those files. Preserve the complete directory and inspect the backup, commit marker state, and installed application before attempting recovery.

## Start Node Core OS

```bash
"$HOME/.node-core/bin/node-core"
```

To expose the launcher in the current shell:

```bash
export PATH="$HOME/.node-core/bin:$PATH"
```

## Validation boundary

CI can test Termux environment detection and dependency selection on GNU/Linux fixtures, but this does not replace a complete installation smoke test on a physical Android device. A Termux-compatible release should only be marked device-validated after the unified installer, Python cryptography/Ed25519 operation, Kubo startup/API, Node Core launcher, and update/data-preservation checks pass on a real Termux ARM64 environment.

For diagnostic evidence, collect:

```bash
uname -m
python3 --version
"$HOME/.node-core/runtime/node-core-venv/bin/python" -c 'import cryptography; from cryptography.hazmat.primitives.asymmetric import ed25519; ed25519.Ed25519PrivateKey.generate(); print(cryptography.__version__, "Ed25519 OK")'
"$PREFIX/bin/ipfs" version
"$HOME/.node-core/bin/node-core" --help
```

If a command fails, preserve its complete output and `~/.node-core/logs/kubo.log`. Do not remove runtime recovery files or user data while troubleshooting.
