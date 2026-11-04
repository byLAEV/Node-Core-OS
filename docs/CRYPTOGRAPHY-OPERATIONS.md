# Cryptographic Runtime Contract and Recovery

**Dependency:** `cryptography>=42.0.0` only. **Self-test:** `python -m node_core.security.crypto_health --json`.

Node Core OS uses Ed25519 for technical node identity/signatures, SHA-256 for node IDs,
PKCS8 PEM serialization and EdDSA/JWS for its current node certificates. This is not
X.509, personhood verification, anti-Sybil protection, zero-knowledge proofs, or
encryption of the persistent private key at rest.

## Platform installation

- GNU/Linux: Python 3.10+, private venv, compatible binary wheels only. Prefer bundled
  wheelhouse, then configured package index. Do not silently compile cryptography or
  install compilers/system headers. If no wheel exists, stop and report Python version,
  architecture and pip error.
- Termux Android ARM64: native `python-cryptography` package through `pkg`; venv
  exposes Termux site-packages. Never install manylinux wheels into Android Python.
- PyNaCl, PyCryptodome, duplicate OpenSSL bindings, Rust, Cargo, C compilers,
  OpenSSL headers and libffi headers are not runtime dependencies.

## Mandatory validation

The shared self-test checks minimum version, Ed25519 generation, signing, successful
verification, rejection of altered message data, PKCS8 PEM round-trip and SHA-256
against the standard digest for `abc`. It uses temporary in-memory keys and never
reads or changes the persistent node identity. Install, verify, update and CI must
run the same test with the exact private runtime interpreter.

## Recovery matrix

| Symptom | Action |
|---|---|
| cryptography import missing | Confirm exact venv interpreter; install declared requirement in that venv only. |
| version below 42.0.0 | Upgrade declared requirement in private venv and rerun self-test. |
| no compatible Linux wheel | Stop; report Python, architecture and pip error; do not compile silently. |
| Termux package unavailable | `pkg update && pkg install python-cryptography`; verify venv visibility. |
| sign/verify, PEM or SHA test fails | Stop installation/update; preserve logs and all identity files. |
| existing identity missing/corrupt/mismatched | Fail closed; never auto-generate a replacement key. |
| update candidate fails | Do not activate; restore previous app and commit marker; retain recovery files if rollback fails. |

## Key protection boundary

The current private key is unencrypted PKCS8 PEM. The store intends directory mode
0700 and key mode 0600. This protects against other local accounts when POSIX
permissions are enforced, not against same-user malicious processes or a compromised
host. Do not introduce passphrase encryption without a versioned migration, consent,
backup, unattended unlock and tested recovery of the exact same key.

Installed-node diagnostic:
```bash
"$HOME/.node-core/runtime/node-core-venv/bin/python" -m node_core.security.crypto_health --json
```
Do not substitute system Python for the installed runtime.
