# CDD Intent Lobby — MVP

**Status:** implementation branch / experimental local MVP. Not a production anti-bot or human-identity proof.

## Intended flow

1. A Web2 site routes an incoming request to a CDD lobby instead of immediately exposing the protected origin.
2. The lobby applies ordinary resource limits and may run an accessible challenge. Challenge success is an input to the lobby, not something a CID proves.
3. The operator maps a small, explicit set of intent names to internal destination IDs and content CIDs. Clients cannot submit arbitrary origin URLs or arbitrary CIDs as destinations.
4. The lobby issues a random opaque handle. The handle contains no CID, intent, domain, path, or destination data.
5. After the configured minimum wait, the handle can be consumed once before expiry. Successful consumption returns an internal grant for the configured destination and CID.
6. The gateway uses the grant to route the request through an operator-controlled destination mapping. It must not turn the grant into an open redirect or an unrestricted proxy.

## Implemented in this MVP

- node_core/security/cdd_intent.py defines configured intent routes, opaque random handles, server-side ticket records, TTL, optional minimum wait, a bounded active-ticket table, expiration cleanup, and consume-once behavior.
- tests/test_cdd_intent.py covers issue/consume, CID not present in the opaque handle, too-early attempts, replay, unknown intent, expiry, and capacity limits.
- The dedicated CDD CI workflow compiles and runs the new tests as an ordinary non-root user.

## Important limitations

- This module is a local in-memory primitive. It is not yet wired into cdd_gateway.py or cdd_router.py, does not itself render a lobby page, and does not yet publish/resolve intent tickets through real Kubo.
- Tickets are stored in one process. A multi-gateway deployment needs an authenticated shared consume-once store or a protocol that safely handles replay across nodes; independent in-memory tables are insufficient.
- The configured CID is a content reference, not a human identity or a proof of authorization. The operator must verify content integrity and authorize the issuer separately.
- Minimum wait is only a friction signal. Bots can wait, and legitimate users can be fast. Do not classify all fast requests as malicious.
- Do not route suspected abuse to an unbounded garbage endpoint: that can waste resources or amplify attacks. A future decoy must be isolated, low-cost, non-reflective, and covered by resource limits.
- This does not defeat volumetric DDoS against the network link. Upstream provider controls, CDN/WAF capacity, and origin isolation may still be required.
- No public web domain, production origin, or external target is used by these tests.

## Next acceptance criteria

1. Add a bounded human-verification challenge endpoint and accessible non-JavaScript fallback; do not claim cryptographic proof of humanness.
2. Add replay tests across two independent gateway processes using a shared durable store.
3. Resolve the configured page/content CID through a real isolated Kubo daemon and verify returned bytes.
4. Add metrics for issued/consumed/expired/replayed tickets without logging raw handles.
5. Test overload, coordinator outage, clock skew, and fail-closed behavior before any public exposure.
