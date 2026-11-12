# NODE-PKI-GUARD CLI — downloadable source bundle

This directory contains a **source snapshot for evaluation and integration**.
It is not a signed production release and must not be represented as one.

## Package

- File: `node-pki-guard-cli-1.0.0-source.zip`
- SHA-256: `041f72b94d10d663e2e0fcd7e33e25ec01938eac3cf6343f1791a752ebab7a2b`
- Checksum file: [SHA256SUMS-1.0.0-source.txt](./SHA256SUMS-1.0.0-source.txt)
- Machine-readable manifest: [release-manifest-1.0.0-source.json](./release-manifest-1.0.0-source.json)

## Download from GitHub

Download the ZIP directly from the repository branch:

```sh
curl -fL \
  "https://raw.githubusercontent.com/byLAEV/Node-Core-OS/feature/node-pki-guard-implementation-v1/Catalog of Products and Services as Business Models for the Node Core OS Identity Node Network by LAEV/Certificates/10-node-pki-guard/releases/node-pki-guard-cli-1.0.0-source.zip" \
  -o node-pki-guard-cli-1.0.0-source.zip
curl -fL \
  "https://raw.githubusercontent.com/byLAEV/Node-Core-OS/feature/node-pki-guard-implementation-v1/Catalog of Products and Services as Business Models for the Node Core OS Identity Node Network by LAEV/Certificates/10-node-pki-guard/releases/SHA256SUMS-1.0.0-source.txt" \
  -o SHA256SUMS-1.0.0-source.txt
sha256sum -c SHA256SUMS-1.0.0-source.txt
unzip -t node-pki-guard-cli-1.0.0-source.zip
unzip node-pki-guard-cli-1.0.0-source.zip
cd node-pki-guard-cli
sh install.sh
```

Requirements: Linux/POSIX, Python 3.10 or newer, OpenSSL 1.1.1 or newer.
The installer uses `pipx` when available; otherwise it installs to the
user's Python environment. It does not install NODE Core OS.

## Commands

```sh
node-pki-guard --version
node-pki-guard verify --help
node-pki-guard verify-receipt --help
```

Use `verify` to validate an X.509 bundle against a CA file and the requested
identity/purpose. Use `verify-receipt` to verify a detached lifecycle receipt
signature. The receipt public key and expected key identifier MUST be
authenticated independently; a receipt cannot establish its own trust anchor.

## Security and release status

- This source snapshot is **unsigned**. SHA-256 detects accidental corruption
  but does not authenticate the publisher or prove provenance.
- Do not use a checksum downloaded from the same untrusted channel as the ZIP
  as a substitute for a digital signature.
- The GitHub Actions release workflow is intended to create Sigstore/Cosign
  bundles and provenance attestations for tagged releases. Those signatures
  do not exist for this source snapshot.
- No private CA key, production root certificate, or organization trust
  anchor is included.
- Generic X.509 verification does not validate NODE UTXO authorization,
  network consensus, or distributed finality.

This bundle becomes a production release only after CI passes, the package is
built from the reviewed commit, its signatures are published and verified,
and the release checklist is approved.
