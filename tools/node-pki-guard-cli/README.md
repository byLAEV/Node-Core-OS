# node-pki-guard-cli

Independent Linux CLI to verify a NODE-PKI-GUARD X.509 bundle without installing NODE Core OS.

## Requirements

- Linux or another POSIX environment.
- Python 3.10 or newer.
- OpenSSL 1.1.1 or newer available as `openssl`.
- A CA trust bundle obtained from a trusted source independently of the certificate bundle.

The verifier uses only Python's standard library at runtime. It does not install the NODE Core OS package, the `cryptography` Python library, or any NODE-specific runtime service.

## Install from the repository

Install using pipx (recommended for an isolated command-line tool):

```sh
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install "git+https://github.com/byLAEV/Node-Core-OS.git#subdirectory=tools/node-pki-guard-cli"
```

Or install into the current user's Python environment:

```sh
python3 -m pip install --user \
  "git+https://github.com/byLAEV/Node-Core-OS.git#subdirectory=tools/node-pki-guard-cli"
```

After installation:

```sh
node-pki-guard --version
node-pki-guard verify --help
```

## Verify a downloaded bundle

Download and extract the public bundle. Obtain the root CA bundle from a trusted channel and compare its fingerprint using an independently authenticated source. Do not trust a root certificate solely because it was included in the same download as the leaf certificate.

```sh
node-pki-guard verify \
  --bundle-dir ./node-pki-guard-bundle \
  --ca-file /etc/node-pki/trusted-roots.pem \
  --hostname service.example.com
```

For an IP identity:

```sh
node-pki-guard verify \
  --bundle-dir ./node-pki-guard-bundle \
  --ca-file /etc/node-pki/trusted-roots.pem \
  --ip 192.0.2.10
```

For a chain with an intermediate CA:

```sh
node-pki-guard verify \
  --bundle-dir ./node-pki-guard-bundle \
  --ca-file /etc/node-pki/trusted-roots.pem \
  --intermediates ./intermediates.pem \
  --hostname service.example.com
```

Require certificate revocation checking using a current CRL:

```sh
node-pki-guard verify \
  --bundle-dir ./node-pki-guard-bundle \
  --ca-file /etc/node-pki/trusted-roots.pem \
  --crl-file ./issuer.crl.pem \
  --require-crl \
  --hostname service.example.com
```

For automation, add `--json` to produce a JSON result. Exit status is 0 for successful verification and 2 for a rejected input or failed check.

## What is checked

1. The manifest format and version.
2. JSON duplicate keys, safe relative paths, and file inventory shape.
3. SHA-256 of every file declared in the manifest.
4. Certificate DER SHA-256 fingerprint and SubjectPublicKeyInfo SHA-256 fingerprint, both compared with the manifest.
5. X.509 path, strict certificate constraints, TLS purpose/EKU, and hostname/IP identity using the installed OpenSSL.
6. CRL status when a CRL is supplied. Use `--require-crl` to fail closed when no CRL is supplied.

The CA file is always supplied separately with `--ca-file`; the bundle and its manifest never define their own trust. The CLI does not fetch trust anchors, CRLs, or OCSP responses.

## What is deliberately not checked

This generic X.509 CLI does not validate the NODE-PKI-BINDING issuer signature, NODE identity JWS signature, UTXO authorization, ledger finality, administrative receipt, or distributed consensus. A manifest may indicate that a NODE binding is present, but generic OpenSSL deployments do not need that sidecar. NODE Core OS nodes must use their NODE-aware verifier for these additional controls.

The CLI verifies already-issued certificates. It does not issue certificates and never needs a CA private key.

## Run tests from this directory

```sh
python3 -m unittest discover -s tests -v
```
