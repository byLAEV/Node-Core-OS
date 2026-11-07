# Repository Coherence Contract

**Applies to:** Node Core OS repository version 1.5.7  
**Machine-readable facts:** [REPOSITORY-CONTRACT.json](REPOSITORY-CONTRACT.json)  
**Status vocabulary:** [Implementation Status and Evidence Policy](IMPLEMENTATION-STATUS-POLICY.md)

## What coherence means

A repository is coherent when every public claim is traceable to the same revision's executable code, declared dependencies, installer behavior, runtime configuration, tests and release metadata. A higher-level description must not promise behavior that the implementation does not deliver. A proposal must not be described as an installed feature. A test result must identify its exact scope, revision and environment.

### Precedence when sources disagree

1. **Executable code** defines what the revision actually does.
2. **Installer, updater, runtime configuration and dependency manifests** define how that code is installed and executed.
3. **Tests and CI evidence** define which behaviors were actually exercised and in which environment.
4. **Technical documentation** explains those facts and their limitations.
5. **README, changelog, catalogs and public summaries** communicate the same facts without expanding their scope.

This order does not mean an adopted security or product requirement should be weakened to match a bug. If implementation violates a requirement, fix the implementation or report the limitation; do not conceal it by changing documentation.

## Canonical 1.5.7 facts

- Repository `VERSION`: `1.5.7`.
- One product and one public installer/updater entry point: `bash update.sh`. The bootstrap validates a downloaded source archive and delegates to `installer/install.sh`; existing installations are handed to the protected updater.
- GNU/Linux is the primary environment. Native Termux Android ARM64 is handled by the same installer with native package selection. Termux detection uses the Linux kernel plus `TERMUX_VERSION` and `PREFIX`, because Android Python may report `platform.system() == "Android"`.
- Python 3.10 or newer; CI currently uses Python 3.12.
- `cryptography>=42.0.0` is a real third-party runtime dependency.
- The Python HTTP client is standard-library `urllib`; third-party `requests` is not a required runtime dependency.
- Kubo GNU/Linux installer baseline: v0.43.1. Termux uses its native `kubo` package.
- `systemd --user` is optional.
- Root and sudo are forbidden for installation, update, tests and normal runtime operation.
- Installed runtime Python: `~/.node-core/runtime/node-core-venv/bin/python`. Compilation, crypto smoke tests, test execution and recovery validation must use this interpreter.
- Updates replace application code and a protected commit marker; they must preserve user data and Kubo state and stop when recovery state is ambiguous.
- Recovery validates dependencies against the recovered application's own manifest. The Ed25519 smoke test is required when that manifest declares `cryptography`; a legacy release without that declaration is not rejected for a dependency introduced later.
- Core GNU/Linux CI uses Node.js 24-compatible `actions/checkout@v5` and `actions/setup-python@v6`. The Actions runtime is independent of the product's Python runtime.

## Product and application boundaries

The repository source tree is not identical to the installed application. The installer removes the suspended HashPaper and P2P Contracts application source from the installed Node Core application tree. Their repository sources, historical documentation and workflows must not be described as bundled active applications in the installed 1.5.7 product.

The installed core includes the terminal BIOS, local storage abstraction, Kubo/IPFS adapter, content registry, technical Ed25519 node identity, locally declared identity profile, My Life records, and network/P2P modules. Each network capability still needs its own evidence; source presence alone does not establish that every transport or distributed protocol is operational.

The technical node key proves control of a key, not civil identity. The local identity profile is declared data, not issuer-verified identity. The technical private key is permission-protected PEM data and is not encrypted at rest by the current identity store.

A stable public API, official SDK, global human uniqueness, production personhood verification, anti-Sybil guarantees, production distributed consensus and zero-knowledge proof system are not complete capabilities in this release unless later code and evidence explicitly establish them.

## Tag and release truth

The repository `VERSION` and Git tag are separate facts. Historical note: tag `1.5.6` was reconciled and published on 2026-11-07 with two archives. Version 1.5.7 is a new release candidate; do not call it published until its CI, exact tag, two archives and checksums are verified.

Do not rewrite or move historical tags as part of a documentation correction. A new release must be created from a reviewed and tested commit with matching VERSION, tag, assets, checksums and release notes.

## Regression rule

Any change to version, platform support, Python dependencies, Kubo pin, installer entry point, runtime interpreter, persistent paths or feature status must update this machine-readable contract and the corresponding documentation in the same change. The coherence test checks selected high-risk relationships. Passing it proves consistency of those checked declarations, not that every feature is operational or every physical environment has been tested.
