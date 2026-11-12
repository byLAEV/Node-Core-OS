# NODE-PKI-GUARD CLI — downloadable source bundle

This directory contains a **source snapshot for evaluation and integration**.
It is not a signed production release and must not be represented as one.

## Package

- File: `node-pki-guard-cli-1.0.0-source.zip`
- SHA-256: `33ff517e87c188030fb9c93cda6d7c63a8d1ee51f1a2c72ff3412365ede18e93`
- Checksum file: [SHA256SUMS-1.0.0-source.txt](./SHA256SUMS-1.0.0-source.txt)
- Machine-readable manifest: [release-manifest-1.0.0-source.json](./release-manifest-1.0.0-source.json)

## Download from GitHub

Download the ZIP directly from the repository branch:

```sh
curl -fL \
  "https://raw.githubusercontent.com/byLAEV/Node-Core-OS/feature/node-pki-guard-implementation-v1/Catalog%20of%20Products%20and%20Services%20as%20Business%20Models%20for%20the%20Node%20Core%20OS%20Identity%20Node%20Network%20by%20LAEV/Certificates/10-node-pki-guard/releases/node-pki-guard-cli-1.0.0-source.zip" \
  -o node-pki-guard-cli-1.0.0-source.zip
curl -fL \
  "https://raw.githubusercontent.com/byLAEV/Node-Core-OS/feature/node-pki-guard-implementation-v1/Catalog%20of%20Products%20and%20Services%20as%20Business%20Models%20for%20the%20Node%20Core%20OS%20Identity%20Node%20Network%20by%20LAEV/Certificates/10-node-pki-guard/releases/SHA256SUMS-1.0.0-source.txt" \
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

## Verify a signed release (when published)

The source ZIP above is unsigned. For the signed GitHub Release, download
the archive and its matching `.sigstore.json` bundle, then verify the
workflow identity and OIDC issuer before extracting:

```sh
cosign verify-blob \
  --bundle node-pki-guard-cli-linux-x86_64.tar.gz.sigstore.json \
  --certificate-identity-regexp '^https://github.com/byLAEV/Node-Core-OS/.github/workflows/node-pki-guard-release.yml@refs/tags/node-pki-guard-v1.0.0$' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  node-pki-guard-cli-linux-x86_64.tar.gz

sha256sum -c SHA256SUMS
gh attestation verify node-pki-guard-cli-linux-x86_64.tar.gz \
  --repo byLAEV/Node-Core-OS \
  --signer-workflow byLAEV/Node-Core-OS/.github/workflows/node-pki-guard-release.yml
gh release verify node-pki-guard-v1.0.0 --repo byLAEV/Node-Core-OS
```

The Sigstore bundle verifies the blob signature and expected CI signer identity.
GitHub's attestation verification separately checks artifact provenance and
workflow identity. These steps become usable only after the signed Release
and attestations have actually been published.
