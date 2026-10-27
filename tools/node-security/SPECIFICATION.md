# Node Security Services — Product Specification

**Status:** Requirements draft.

## Intended service

Provide bounded security controls for authorized node interactions: authentication, action-specific authorization, rate limiting, abuse detection, credential/revocation checks, and verifiable audit events.

## Security requirements

- A successful authentication must not imply permission for every operation.
- Rate limits and burst limits are enforced by the receiving service, not trusted from client-provided fields.
- Anomaly handling and quarantine rules must be explicit, observable, proportionate, and recoverable.
- Use replay-resistant challenges when current proof of key control is required.
- Protect private keys and administrative endpoints; do not expose Kubo administrative RPC as a general application API.
- Define log minimization and retention to avoid collecting unnecessary identity data.
- Document denial-of-service assumptions and limits; certificates alone cannot prevent resource exhaustion.

## Acceptance tests

Cover unauthorized operations, rate-limit exhaustion, malformed requests, replayed challenges, revoked credentials, service failure, log redaction, and safe recovery from quarantine.
