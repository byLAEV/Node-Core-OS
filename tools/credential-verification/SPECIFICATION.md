# Credential Verification — Product Specification

**Status:** Requirements draft.

## Intended service

A verifier should report a structured result for a supplied credential: encoding/profile validity, signature result, issuer trust decision, validity window, revocation status and the scope of the conclusion. It must not collapse all checks into a single unqualified “identity verified” result.

## Required output distinctions

- `format_valid`: the credential conforms to the declared schema.
- `signature_valid`: the signature matches the defined signed bytes and public key.
- `issuer_trusted`: the issuer is trusted under an explicitly configured policy.
- `time_valid`: the credential is within its validity interval.
- `revocation_status`: valid, revoked, unknown, or stale/unavailable according to policy.
- `claim_verification`: which real-world claims were checked, by whom, how, and with what evidence.
- `authorization_decision`: whether the requested action is allowed; this is a separate policy result.

Unknown or unavailable revocation status must not silently become “not revoked.” Failed checks must return actionable, non-secret errors.

## Acceptance tests

Test malformed data, invalid signatures, unknown issuers, expiry, revocation, stale revocation data, wrong purpose/scope, tampering, and authorization denial. Document trust-store updates and audit logging.
