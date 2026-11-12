# NODE-PKI-GUARD Standalone Lifecycle Service

Status: implementation in progress; not a production certification claim.

## Scope

`PKILifecycleService` orchestrates the Standalone certificate issuance path.
It stages the exact X.509 certificate in a durable SQLite operation record
before consuming the authorization UTXO. It then delegates the atomic spend to
the configured UTXO backend, verifies the backend's commit evidence through
the shared coordinator, signs an issuance receipt with the configured CA key,
and marks the lifecycle operation COMMITTED.

The Standalone backend proves a local SQLite ACID commit only. It does not
prove distributed consensus, global uniqueness, or Network finality.

## State machine

```text
NEW
 |
 | validate request digest and PROTECTED decision
 v
PREPARED  -- certificate PEM + fingerprint durably stored
 |
 | consume_authorization(idempotency_key)
 | verify backend-specific commit evidence
 v
COMMITTED -- signed receipt + transaction ID + commit kind stored
```

A failed or interrupted operation remains PREPARED. Recovery calls `issue()`
again with the identical request, decision and idempotency key. The staged
certificate is reused; the backend coordinator returns the original durable
spend result for the same idempotent request. The caller must not substitute a
new CSR or authorization.

## Receipt

The receipt binds the operation ID, idempotency key, request and operation
hashes, authorization ID and outpoint, certificate fingerprint, backend
transaction ID, commit kind, commit time, issuer trust fingerprint, and
issuance profile version. The CA signing key signs the canonical JSON receipt.
The public key corresponding to the pinned CA certificate verifies it.

## Security boundaries

- The CSR's proof-of-possession and issuance profile are checked by the
  X.509 issuer primitive.
- A trusted application boundary must validate the NODE identity credential,
  X.509 chain/hostname/EKU/revocation, signed NODE-PKI-BINDING, challenge
  freshness and both proof-of-possession signatures, authorization signature
  requirements, policy, and authoritative UTXO record before passing a
  PROTECTED decision to this service.
- The service checks that the decision and immutable spend request agree and
  recomputes the spend request digest.
- The backend's commit evidence is verified before COMMITTED is persisted.
- A receipt is signed evidence of the recorded operation, not a replacement
  for trust-anchor distribution, certificate path validation, or UTXO state.
- The service is not a network-facing API and must not accept a caller-created
  `AuthorizationDecision` as proof of identity or authorization.
- No private CA key is written into the lifecycle database.

## Database compatibility

The lifecycle database has its own schema version. The Standalone UTXO
database was upgraded to schema version 2 with a nullable
`authorization_payload_hash` commitment column. Existing v1 databases are
upgraded in place; legacy rows without the full-document commitment remain
uncommitted/legacy and must not be treated as cryptographically bound to a
complete authorization JSON object.

## Required acceptance tests before v1.0

- End-to-end issue using a generated CA, CSR, binding, identity credential,
  dual proof, signed authorization and real Standalone SQLite backend.
- Retry after PREPARED and before UTXO spend.
- Retry after UTXO spend and before lifecycle COMMITTED.
- Same idempotency key with changed CSR, authorization or request content.
- Concurrent attempts with one authorization outpoint.
- Receipt tampering and public-key verification.
- OpenSSL verification of the exact issued PEM and CRL revocation behavior.
- Process termination/restart tests against persistent database files.
- Independent review of authorization signature verification and trust
  distribution before any public production release.
