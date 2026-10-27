# CMI / SCC — Product Specification

**Status:** Draft proposal. Not a production certificate profile.

## Purpose

Define a future credential lifecycle for a personal identity anchor (CMI) and subordinate device/node credentials (SCC). This document is a product and requirements boundary; it does not assert that an issuer, CA, certificate registry, or revocation service is operational.

## Intended responsibilities

- Define issuer, subject, device, key, and credential identifiers without conflating them.
- Define credential versioning, canonical serialization, signature algorithm, key encoding, and exact signed bytes.
- Support issuance, verification, expiry, renewal, revocation, key rotation and delegated permissions.
- Record evidence of verification: who or what checked a claim, the method, scope, time and result.
- Keep permissions scoped to explicit operations and enforce them at the service boundary.
- Permit a device credential to be revoked or replaced without silently redefining the person's identity.

## Required distinctions

- A key pair identifies a cryptographic control capability, not necessarily a human.
- A signature validates integrity and key-level authorship, not the real-world truth of every field.
- A `persona_hash` or `zk_proof_hash` is not proof of uniqueness or proof of a claim by itself.
- A reputation score or count of historical records has no reliable meaning until its source, semantics, weighting, and dispute process are specified.
- A field such as `political_voting_power: false` does not enforce authorization; policy must reject unauthorized voting actions.
- A certificate is not a substitute for authenticated transport, access control, abuse protection or a Sybil-resistance design.

## Before implementation can be called verified

1. Publish a deterministic, versioned encoding and signed-field definition.
2. Specify a trust model and how issuers are authorized.
3. Specify validity periods, revocation distribution, freshness and rollback behavior.
4. Validate key and signature lengths/encodings strictly; reject malformed and ambiguous input.
5. Define proof-of-possession and replay protection for operations that require current control of a key.
6. Add tests for issuance, validation, tampering, wrong issuer, expired credentials, revoked credentials, key rotation and invalid permissions.
7. Document private-key generation, storage, backup and recovery without shared private keys.
8. Obtain security review before production deployment.

## Non-goals

This specification does not establish universal human uniqueness, legal identity acceptance in every jurisdiction, automatic trust, automatic payment, or guaranteed earnings. Those require separate evidence, governance, business and legal processes.
