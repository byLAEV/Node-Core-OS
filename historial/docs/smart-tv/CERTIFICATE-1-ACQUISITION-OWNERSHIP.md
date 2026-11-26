# Smart TV Credential 1 — Acquisition and Ownership

**Status:** version 1 proposal. The schema and examples are not an implemented issuer or a legal title registry.

## Objective

Represent manufacturer provenance, device-key binding, an owner claim, and ownership transfers as distinct signed statements. Never infer ownership solely from possession of a device key or from a manufacturer attestation.

## Claims and actors

- **Manufacturer issuer:** signs manufacturing provenance and binds a device identifier to a device public key or hardware-backed attestation.
- **Device:** proves control of the enrolled private key, preferably protected by a secure element/TEE where the platform supports it.
- **Owner:** signs an ownership claim using an owner-controlled key.
- **Transfer parties:** authorize transfer according to a versioned transfer policy.
- **Verifier:** checks signatures, issuer trust, expiry, revocation, chain links, and policy; it must not assume legal identity unless a separate process established it.

## Proposed credential envelope

This is an application-level JSON proposal, not the existing Node Core OS JWS certificate format. Production issuance must define canonical signing bytes and a strict JSON Schema before signing is implemented.

```json
{
  "schema": "node-core-os.smart-tv.acquisition-ownership",
  "version": "1.0",
  "credential_id": "urn:uuid:REPLACE-WITH-UUID",
  "device": {
    "manufacturer_id": "manufacturer-namespace",
    "model_id": "model-family",
    "device_id": "opaque-device-reference",
    "device_key_id": "device-key-reference",
    "device_public_key": {
      "type": "Ed25519",
      "public_key_hex": "64-hex-character-public-key"
    }
  },
  "manufacturer_attestation": {
    "issuer_key_id": "manufacturer-key-id",
    "issued_at": "RFC3339-UTC",
    "expires_at": "RFC3339-UTC",
    "signature": "base64url-signature"
  },
  "ownership_claim": {
    "owner_key_id": "owner-key-reference",
    "claim_type": "initial-claim|transfer",
    "effective_at": "RFC3339-UTC",
    "previous_credential_id": null,
    "signature": "base64url-signature"
  },
  "status": {
    "revocation_registry": "configured-status-reference",
    "checked_at": "RFC3339-UTC"
  }
}
```

The example is a field-level contract only. A production schema must constrain enums, timestamps, string sizes, public-key encoding, signature encoding, unknown fields, and whether fields may be null. Duplicate JSON keys and ambiguous canonicalization must be rejected.

## Issuance and transfer protocol

1. Manufacturer creates a device identity during manufacturing and signs a provenance statement using a protected issuer key.
2. Device proves possession of its device key using a challenge-response protocol. Never transmit its private key.
3. Owner initiates acquisition enrollment and signs a challenge linking the owner key, device credential ID, and intended claim.
4. Verifier checks manufacturer trust, signature, device-key proof, revocation/status, expiry, and replay protection.
5. The system records a signed acquisition receipt. Personal details should remain local or be represented by a privacy-preserving reference unless disclosure is necessary and consented.
6. Transfer requires a new signed transfer statement referencing the prior credential, proof of control by the current owner where available, acceptance by the new owner, and policy-defined recovery for lost keys or unavailable sellers.
7. Verifiers reject stale, revoked, conflicting, or incomplete transfer chains and expose the reason without silently selecting an owner.
8. Recovery and dispute resolution are separate policy procedures; cryptographic verification does not itself resolve legal disputes.

## Required negative tests

- invalid manufacturer signature;
- device public key mismatch;
- missing device key proof;
- invalid owner signature;
- expired or revoked manufacturer/device credential;
- duplicate credential ID or replayed challenge;
- transfer with missing or inconsistent predecessor;
- conflicting transfer claims;
- malformed timestamp, key, signature or schema;
- untrusted manufacturer key;
- privacy test proving private keys and unnecessary personal data are not emitted.

## Acceptance criteria

A verifier accepts only a structurally valid, correctly signed chain under an explicitly configured trust policy. It must distinguish **manufacturer-attested**, **device-key possession verified**, **owner-key claim verified**, **transfer chain verified**, and **legal ownership not independently determined**. No test may label a valid signature as proof of legal ownership.
