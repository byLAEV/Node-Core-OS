# Node Core OS — Intent Certificate Protocol (prototype specification)

**Status:** experimental design and simulation fixture; not production-ready and not yet a supported Node Core OS feature.

## 1. Purpose

Represent a request's declared purpose, authorized scope, evidence of scope justification, and current defensive state in a machine-readable certificate chain. The goal is to evaluate a prototype before integration with the Node Core runtime or live network traffic.

A declaration does not prove that a requester is human, benign, or truthful. A valid signature proves integrity and possession of a signing key; authorization and observed behavior remain separate checks.

## 2. Three sequential layers

1. **General certificate (`general`)** — establishes the broad class of intended activity and maximum allowed scope.
2. **Specific certificate (`specific`)** — narrows resource and operation scope. It must not grant more than its parent.
3. **Demonstration certificate (`demonstration`)** — binds a justified operation/request family to the previous certificates and is evaluated against explicit policy rules and observed behavior.

A website's policy may describe its complete resource catalogue, but a client certificate must never inherit unrestricted access merely because a global policy exists. Each client receives only the smallest scope the service explicitly authorizes.

## 3. Prototype fields

The simulator uses JSON objects with these fields:

- `schema_version`: protocol schema version (`1.0` in this prototype).
- `certificate_id`: identifier within the issuer's namespace.
- `certificate_type`: `general`, `specific`, or `demonstration`.
- `issuer`: policy issuer identifier.
- `subject`: technical client identifier, not a civil-identity claim.
- `intent`: stable machine-readable intent identifier.
- `parent_certificate_id`: parent ID; absent only on the general certificate.
- `scope.resources`: resource patterns permitted by policy.
- `scope.operations`: permitted operations, such as `GET`.
- `issued_at`, `expires_at`: timezone-aware ISO 8601 timestamps.
- `status`: `active` or `revoked` in the fixture.
- `demonstration`: purpose and justification (demonstration certificate only).
- `limits.requests_per_minute`: request limit for the demonstration certificate.
- `signature`: HMAC-SHA256 over canonical JSON in the simulator only.

The HMAC key is a synthetic shared secret used only to make the example reproducible. It is **not** suitable for production because every verifier sharing the key could also issue certificates. Production must select an established asymmetric signature format, issuer/key discovery, key rotation, strict validation, revocation distribution, replay protection, and canonicalization rules before deployment.

## 4. Admission decision

The prototype checks:

1. Certificate existence and signature integrity.
2. Supported schema version and validity interval.
3. Revocation state.
4. Complete chain and expected certificate order.
5. Parent-child scope narrowing.
6. Exact match between request intent and demonstration intent.
7. Non-empty justification and requested resource/operation scope.
8. Risk state and rate limit.

A `suspect` certificate is not automatically revoked. In the prototype, an otherwise in-scope request is temporarily restricted to `GET` and one request per minute. A revoked, invalid, expired, or out-of-scope certificate is denied. These are sample policy decisions, not universal defaults.

## 5. Defensive states

- `ACTIVE`: ordinary policy applies.
- `SUSPECT`: reversible restriction pending further evidence.
- `REVOKED`: issuer-authorized invalidation; protected requests are denied.
- `EXPIRED`: certificate is outside its validity interval.

A production revocation event needs an authorized issuer, reason code, issue/effective times, freshness policy, and signature. Receivers must reject forged, stale, replayed, or unauthorized events. One untrusted node must not be able to revoke every participant's certificates.

## 6. Threat model and limitations

The prototype is local and deterministic. It does not receive network traffic, issue public-key certificates, prove personhood, prevent DDoS, establish cross-node consensus, persist revocation state, or protect a production web service. It does not infer the truth of an intent from a string.

Production work must consider:

- false or misleading intent declarations;
- compromised or stolen credentials;
- replay and certificate sharing;
- Sybil clients and distributed rate-limit evasion;
- malicious/forged revocation and suspicion messages;
- stale policy and revocation caches;
- denial-of-service against the validator itself;
- privacy leakage through stable identifiers and intent telemetry;
- false positives against legitimate bots and users;
- resource exhaustion before certificate validation can run.

The certificate layer complements TLS, server-side authorization, application rate limits, bot detection, and network/transport DDoS mitigation. It does not replace them.

## 7. Run the simulation

GNU/Linux, normal user, Python 3.10+, no third-party packages:

```bash
python3 tools/intent_certificate_simulator.py --demo --pretty
python3 -m unittest discover -s tests -p 'test_intent_certificate_simulator.py' -v
```

Initial acceptance criteria:

- valid in-scope request is allowed;
- out-of-scope resource/operation is denied;
- intent mismatch is denied;
- invalid signatures and expired certificates are denied;
- revoked certificates are denied;
- suspicion causes reversible restriction, not automatic permanent revocation;
- rate limit is enforced deterministically;
- metrics count decisions without recording user personal data.

Before any production claim, add asymmetric signatures, strict schema validation, issuer authorization, key lifecycle, replay protection, distributed quota coordination, privacy review, fuzz/property tests, load tests, and integration tests at the actual enforcement point.
