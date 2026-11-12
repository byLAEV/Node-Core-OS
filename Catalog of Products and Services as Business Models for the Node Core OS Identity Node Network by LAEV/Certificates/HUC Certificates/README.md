# HUC Certificates

**HUC Direct SDK — integration and certificate lifecycle workspace**

This directory is the dedicated home for HUC certificate materials and the HUC Direct SDK integration layer. It is kept separate from NODE-PKI-GUARD: HUC credentials and issuer attestations are a distinct product/protocol scope and must not be represented as interchangeable with X.509 PKI authorization.

## Scope

The directory is intended to hold:

- HUC credential and certificate profiles, schemas, and lifecycle specifications.
- HUC Direct SDK source and distributable packages for Python, Android/Kotlin, and TypeScript.
- REST API contracts and reference implementation for institutional integrations.
- Demonstration fixtures using synthetic identities and test-only keys.
- Reproducible tests, compatibility matrices, security notes, and release evidence.
- Checksums, signatures, attestations, and release instructions for published artifacts.

## Proposed layout

```text
HUC Certificates/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SECURITY.md
│   ├── API.md
│   └── INTEGRATION.md
├── python/
├── android/
├── typescript/
├── api/
├── examples/
├── tests/
└── releases/
```

Only add directories when their corresponding source or documentation is committed. Do not place private keys, issuer secrets, production tokens, or real personal identity data in this repository.

## Architecture boundaries

- **Issuer:** creates credentials and issuer-signed attestations. Issuer private keys remain in protected issuer infrastructure.
- **Holder:** creates or controls its own private key, requests credentials, and stores its credential package.
- **Verifier:** validates credential signatures, issuer trust, validity/status evidence, and—when required—fresh proof of possession.
- **Status refresh:** may obtain updated issuer evidence without reissuing the underlying credential, according to the versioned protocol contract.

Android key custody, Python lifecycle operations, REST API behavior, and TypeScript integration must have explicit versioned interfaces and independent tests.

## Security and interoperability requirements

1. Clearly distinguish issuer signature validity, credential status, proof of key possession, and real-world identity verification.
2. Treat offline verification as bounded by the freshness and provenance of the available status evidence.
3. Make challenge-response nonces unpredictable, single-use, scoped, and expiry-bound; reject replay.
4. Never log or distribute private keys, administrative tokens, or sensitive identity payloads.
5. Use synthetic test fixtures in public examples.
6. Verify X.509 interoperability with supported OpenSSL versions where X.509 is part of the profile.
7. Publish artifacts only with reproducible build/test evidence, SHA-256 checksums, and verifiable release signatures/attestations.

## Implementation and release status

The supplied project brief describes **HUC Direct SDK 0.8.0** with Python, Android/Kotlin, REST API, TypeScript, documentation, tests, and a Python wheel. That description is recorded as an incoming implementation claim, not as independently verified repository evidence.

At the time this directory is introduced, the SDK source tree, wheel, demonstration bundle, checksums, and build/test reports have not yet been imported or verified in this repository. Do not describe the SDK as installable or production-ready until the actual artifacts are committed and their tests and integrity checks pass.

## Relationship to other certificate products

- [Certificate catalog](../README.md)
- [NODE-PKI-GUARD](../10-node-pki-guard/README.md)
- [Certificate test and evidence matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md)

HUC and NODE-PKI-GUARD may interoperate through documented adapters, but neither protocol's trust model or security guarantees may be silently attributed to the other.
