# Node Core OS Update Package V2

## Purpose

Package V2 updates an existing Node Core OS installation without bundling or reinstalling Kubo/IPFS. It is separate from the initial installer at `installer/install.sh`.

## Scope and safeguards

- Requires an existing installation at `~/.node-core/app` (or `NODE_CORE_DATA_DIR/app`).
- Downloads the selected Node Core repository branch's latest commit archive.
- Checks that the downloaded source contains `main.py` and `node_core/`.
- Compiles the Python source before replacing the installed application.
- Creates a temporary backup of the existing application before replacement.
- Replaces only the application directory.
- Records the source commit in `runtime/node-core-commit` and package version in `runtime/node-core-version`.
- Does not call Kubo installation, initialization, or service-management commands.
- Does not intentionally modify `config.json`, `storage/`, `ipfs/`, Kubo binaries, or Kubo services.
- Restores the application backup if replacement or compilation fails.

## Run

From the repository checkout:

```bash
bash installer/update-v2.sh
```

To select a different repository branch:

```bash
NODE_CORE_BRANCH=main bash installer/update-v2.sh
```

To select a non-default installation directory:

```bash
NODE_CORE_DATA_DIR="$HOME/.node-core" bash installer/update-v2.sh
```

## Versioning

The package version is declared in `installer/version-v2.json`. The package version and application source commit are distinct identifiers: package version describes the updater's behavior, while the commit SHA identifies the exact source installed.

This initial V2 package tracks the configured branch (default: `main`); it is not a signed or immutable release artifact. For reproducible deployments, publish a GitHub Release and change the package to target a specific tag or commit.

## Verification limits

The package checks Python compilation but does not claim to have run a full live installation test on every supported host. Test it on a disposable or backed-up installation before using it on a node with important data.
