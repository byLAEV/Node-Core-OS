# LAN identity proof protocol (NIP-1)

**Status:** implementation groundwork; pure protocol functions and unit tests only.
This document does not claim a network listener, automatic LAN handshake, or
authenticated peer session is deployed.

## Purpose

Prove that a discovered node controls the Ed25519 private key corresponding to
its advertised node ID. The verifier generates a fresh 256-bit random challenge.
The responding node signs a canonical transcript containing the protocol purpose,
version, complete challenge, node ID, and public key.

## Message flow

1. Verifier creates `IDENTITY_CHALLENGE` with a cryptographically random 32-byte nonce.
2. Responder validates the exact challenge schema and signs the canonical transcript.
3. Responder returns `IDENTITY_PROOF` containing node ID, public key, and signature.
4. Verifier checks key length, derives the node ID from the public key, and verifies
   the Ed25519 signature over the exact challenge.
5. Verifier records only that key possession was proven for this challenge.

## Security boundaries

- A challenge must be fresh for each attempt and must be retained only for the
  bounded lifetime of that attempt. A response to an old challenge is invalid
  for a new challenge.
- The caller must enforce socket timeout, maximum message size, one response per
  challenge, and close the one-shot connection after verification.
- This protocol does not encrypt traffic. Do not send private data or application
  messages through it.
- A valid proof does not establish reachability, authorization, trust, or an
  application session.
- Trust remains explicit through the existing peer trust store and certificate
  pinning flow. Revocation remains authoritative.
- This first implementation is a pure protocol module. Network transport,
  rate limiting, bounded concurrent handlers, expiry cache, and runtime/UI
  integration are separate acceptance work and must not be inferred from unit tests.

## Tests

`python -m unittest tests.test_p2p_identity_proof -v`

Tests cover fresh challenge proof, altered challenge, identity substitution,
tampered signature, malformed challenge, replay against a new challenge, and
bounded response shape. They do not constitute a two-host LAN integration test.
