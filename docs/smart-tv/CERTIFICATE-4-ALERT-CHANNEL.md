# Smart TV Credential 4 — Security Alert and Telemetry Channel

**Status:** protocol proposal. No production Smart TV transport, OEM integration, or live node-network response is claimed.

## Objective

Provide a bounded, authenticated, privacy-minimized path for a TV to notify configured recipients and eligible Node Core OS identity nodes about a local security event.

## Transport requirements

- Use an authenticated transport appropriate to the platform (for example TLS with pinned/configured trust or mutually authenticated TLS where operationally supportable).
- Sign the event independently when it must remain verifiable after transport termination or be relayed between nodes.
- Define a strict event schema, maximum payload size, maximum event rate, retry budget, queue capacity, expiry, replay cache, and back-pressure.
- Authenticate and authorize recipients; do not broadcast sensitive event contents to every discovered peer.
- Encrypt in transit. If evidence is stored or distributed through IPFS, encrypt sensitive evidence before publication and distribute decryption capability only to authorized recipients. A CID is an integrity/content address, not confidentiality or availability.
- Do not send raw microphone/camera recordings, passwords, private keys, session tokens, or unrelated personal data by default.
- Require owner consent and a visible policy for optional diagnostic telemetry. Separate security-critical local checks from optional external telemetry.

## Event envelope proposal

```json
{
  "schema": "node-core-os.smart-tv.security-event",
  "version": "1.0",
  "event_id": "urn:uuid:REPLACE-WITH-UUID",
  "device_ref": "opaque-device-reference",
  "device_key_id": "device-key-reference",
  "observed_at": "RFC3339-UTC",
  "expires_at": "RFC3339-UTC",
  "severity": "info|low|medium|high|critical",
  "category": "firmware-integrity|network-anomaly|privacy-control|availability|credential",
  "result": "observed|blocked|degraded|recovered",
  "evidence": {
    "digest_algorithm": "sha256",
    "digest_hex": "64-hex-character-digest",
    "content_ref": null
  },
  "policy_version": "policy-version",
  "signature": {
    "algorithm": "EdDSA",
    "key_id": "device-key-reference",
    "value": "base64url-signature-over-canonical-unsigned-event"
  }
}
```

The fields above are illustrative. Before deployment, freeze a strict JSON Schema, canonical signing format, supported algorithms, clock-skew rules, and schema migration behavior. The signature must cover every security-relevant field except the signature itself.

## Processing protocol

1. Local sensor or firmware verifier produces an event under an allowlisted event taxonomy.
2. Local validator checks schema, size, time, evidence digest, and local rate limits.
3. Device signs the canonical event with its enrolled key; private key material remains in protected storage.
4. Transport authenticates the device and configured receiver. Receivers validate event signature, key status, expiry, replay ID, policy version and recipient authorization.
5. The origin node reports observations; witness nodes independently corroborate. Signature count alone is not an independence guarantee.
6. Node network returns a structured status: unconfirmed, corroborated, policy-confirmed, rejected, or unable-to-verify.
7. Local policy determines whether to alert the owner, rate-limit a connection, block a specific request, or request support. Remote alerts are not executable commands.
8. Events are deduplicated, bounded in storage, and reconciled after connectivity returns.
9. Report detection, delivery, corroboration, action and recovery latency, along with missing peers and stale trust data.

## Failure behavior

- WAN unavailable: retain only a bounded queue; local protections continue; show that remote corroboration is unavailable.
- Invalid signature or replay: reject without disruptive action and record a bounded diagnostic.
- Flood: rate-limit by authenticated source and local resource budgets; prioritize local safety events; never let alert traffic starve core TV functions.
- Stale revocation or trust state: return an explicit indeterminate result; apply operation-specific fail-open/fail-closed policy.
- Suspected compromised device: do not trust its own alert as proof of compromise; corroborate with firmware measurement, network evidence or independent observations.

## Required tests

Schema/signature tampering, replay, expired event, revoked key, unknown key, duplicate event ID, oversized payload, flood/back-pressure, WAN partition, malicious peer, unauthorized recipient, evidence digest mismatch, corrupted IPFS content, restart with queued events, recovery/reconciliation, false-positive alert, and privacy leakage scan.

## Metrics

Record local detection latency, delivery latency, corroboration latency, eligible peer coverage, dropped/expired events, replay rejection, CPU/memory/queue ceilings, false-positive rate, and recovery time. Do not promise real-time global awareness across a partition.
