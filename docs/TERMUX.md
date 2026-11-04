# Node Core OS on Termux (Android)

This is the native Termux installation path. It does not install Debian, Ubuntu, PRoot, or another Linux distribution.

## Supported environment

- Official Termux app with its package repositories configured.
- Android ARM64/aarch64.
- A normal Termux user session; never run the installer as root or with sudo.
- Network access to the Termux package repository and GitHub.

Automated CI tests validate the wrapper and preservation logic on GNU/Linux using fixtures. They do not replace a real-device Android smoke test. Termux support must be considered device-validated only after the complete install and runtime checks pass on Android.

## Fresh installation

Download the latest **Node Core OS installer source archive** and its matching SHA-512 file from the [official releases page](https://github.com/byLAEV/Node-Core-OS/releases). Extract the archive, enter its directory, and run:

```bash
tar -xzf node-core-os-installer-VERSION.tar.gz
cd node-core-os-installer-VERSION
bash installer/termux-install.sh
```

Replace `VERSION` with the version in the downloaded filename. Run the script inside Termux, not from a GNU/Linux shell or a PRoot distribution.

The Termux wrapper checks the platform and installs only missing Termux packages. It requires the Termux-native `python-cryptography` package and Kubo package. The Python virtual environment is created with access to Termux's system packages; the installer does not attempt to install GNU/Linux manylinux wheels into Android Python.

## Existing installation and recovery

The wrapper never overwrites an existing application as a fresh install. If it detects an existing Node Core OS application, it delegates to the updater. The updater preserves:

- `~/.node-core/storage/`
- `~/.node-core/ipfs/`
- `~/.node-core/config.json`, except for the explicitly required Kubo executable path migration
- The existing Termux Kubo executable at `$PREFIX/bin/ipfs`

If the updater reports pending recovery files under `~/.node-core/runtime/update`, stop. Do not delete or rename those files. Preserve the complete directory and inspect the backup, commit marker state, and installed application before attempting recovery.

## Start Node Core OS

After a successful installation:

```bash
"$HOME/.node-core/bin/node-core"
```

To make the launcher available in the current shell:

```bash
export PATH="$HOME/.node-core/bin:$PATH"
```

## Evidence required for a real-device validation

After installation, collect the output of:

```bash
uname -m
python3 --version
"$HOME/.node-core/runtime/node-core-venv/bin/python" -c 'import cryptography; from cryptography.hazmat.primitives.asymmetric import ed25519; ed25519.Ed25519PrivateKey.generate(); print(cryptography.__version__, "Ed25519 OK")'
"$PREFIX/bin/ipfs" version
"$HOME/.node-core/bin/node-core" --help
```

If a command fails, preserve its complete output and the Kubo log at `~/.node-core/logs/kubo.log`. Do not remove runtime recovery files or user data while troubleshooting.
