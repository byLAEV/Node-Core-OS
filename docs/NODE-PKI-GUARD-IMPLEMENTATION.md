# NODE-PKI-GUARD v1.0 — Local Implementation Contract

## Scope

This implementation adds two JSON Schema documents, local cryptographic proof-of-possession verification, and a fail-closed policy evaluator.

It does not implement or claim a production X.509 trust store, CA, hostname/EKU validator, revocation client, UTXO ledger, transaction submission, consensus, finality, distributed replay protection, double-spend prevention, or exactly-once execution across external systems.

The caller MUST independently validate the X.509 chain, expected service name, validity, key usage/EKU, and revocation status. The caller must pass the public key from that validated certificate into the dual proof verifier.

## Files

- schemas/node-pki-binding.schema.json: NODE-PKI-BINDING v1.0.
- schemas/node-pki-auth-utxo.schema.json: NODE-PKI-AUTH-UTXO v1.0.
- node_core/security/node_pki_guard.py: canonical challenge encoding, proof signatures, fingerprint helpers, binding/auth validation, and policy evaluation.
- tests/test_node_pki_guard.py: local positive and negative tests.

## Cryptographic profile

Dual Proof-of-Possession signs the exact same challenge bytes with both the NODE identity key and the X.509 subject private key.

Supported signature suites:

- Ed25519.
- RSA-PSS with SHA-256, MGF1-SHA-256, and a 32-byte salt.
- ECDSA with SHA-256.

The X.509 public key is extracted from the independently validated certificate. This module does not infer trust from a self-signed or merely parseable certificate.

The challenge includes a 32-byte-or-longer cryptographic nonce, challenge ID, identity, certificate and SPKI fingerprints, purpose, audience, operation hash, and short validity window. Challenge replay storage in this first implementation is process-local and is not a distributed replay defense.

## Canonicalization

The helper emits deterministic UTF-8 JSON with sorted ASCII object keys, compact separators, and unescaped Unicode string values. It intentionally rejects floating-point numbers, non-ASCII object keys, unsafe integers, and unsupported types.

This is a restricted interoperable profile, not a complete general-purpose RFC 8785 implementation. If future fields require general JCS semantics, adopt a reviewed RFC 8785 implementation and publish cross-language test vectors before changing the protocol version.

## Authorization decisions

- STANDARD: requires successful conventional X.509 validation; no UTXO is queried or consumed.
- PROTECTED: requires X.509 validation, verified dual proof, active binding, operation and audience match, canonical operation hash match, valid consensus epoch, and an authorization outpoint returned by the injected authoritative UTXO view.
- DENY: rejects the operation.

The evaluator only returns a decision. A PROTECTED decision is a precondition result, not permission to execute immediately. The future ledger adapter must atomically submit the outpoint spend, wait for documented network finality, and only then invoke an idempotent executor. A local in-memory map is suitable only for unit tests and must never be represented as distributed consensus.

## Run tests

Run the following commands from the repository root:

    python -m unittest tests.test_node_pki_guard -v
    python -m unittest tests.test_node_identity_certificate -v

No test in this module proves multi-node consensus or production interoperability.


## v1.1 adapters added

### OpenSSL X.509 adapter

- Module: node_core/security/node_pki_guard_x509.py
- Uses the OpenSSL verify command with an explicit caller-supplied CA bundle.
- Requires exactly one expected peer identity: DNS hostname or IP address.
- Applies sslserver or sslclient purpose checks, strict X.509 path checks, authentication level, and chain depth.
- Accepts caller-supplied intermediate certificates.
- Supports caller-supplied CRL bundles and explicit leaf-only or full-chain CRL checking.
- Does not download CRLs, perform OCSP, or refresh revocation data. Revocation is only checked when a CRL bundle is provided. Deployments that require revocation must set require_crl and provide a current CRL bundle.
- Uses a temporary directory with restrictive file permissions and a subprocess timeout. OpenSSL 3 disables implicit CA store sources so only the configured CA file is used.

The adapter is an explicit validation boundary. Applications must call it before dual proof verification and pass the public key extracted from the validated certificate. A valid result is not a binding authorization.

### UTXO backend contract

- Module: node_core/security/node_pki_guard_utxo.py
- Defines the UTXOAuthorizationBackend protocol, spend request/result structures, finality proof structure, and consume_authorization coordinator.
- Requires backend-side atomic outpoint consumption, concurrent double-spend rejection, durable idempotency, conflict detection for reused idempotency keys, and independently verifiable finality proofs.
- The coordinator rejects non-PROTECTED decisions and mismatched operation hashes, authorization IDs, and outpoints.
- A protected external operation MUST NOT execute until consume_authorization returns a verified finalized result.

No production ledger adapter, consensus algorithm, distributed storage, or network finality implementation is included. The unit-test fake backend is not a ledger and proves no distributed guarantees.

### v1.1 test commands

    python -m unittest tests.test_node_pki_guard tests.test_node_pki_guard_x509 tests.test_node_pki_guard_utxo -v
    python -m unittest tests.test_node_identity_certificate -v
