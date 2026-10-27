# Node Core OS byLAEV — CID Distributed Defense (CDD)

**Version:** experimental MVP 0.2  
**Status:** signed-policy primitives and local HTTP gateway implemented; not a production edge or DDoS mitigation service.

## Goal

CDD is an incremental architecture for protecting existing Web2 domains, HTTP services and APIs with multiple ingress nodes, signed security policies, request-abuse controls and future P2P discovery. Protected websites and origins do not need to migrate to IPFS.

## Implemented

- Signed, versioned policy creation and verification using the repository's existing Ed25519 node identity.
- Strict policy validation, issuer allowlisting, key-to-node-ID binding, expiry checks and anti-rollback sequence.
- Bounded in-process sliding-window request limiting.
- Kubo adapter helpers that publish the exact signed JSON policy bytes using `KuboManager.add_file(pin=True)` and load them using `KuboManager.cat(cid)`, then verify the signature.
- A laboratory HTTP reverse proxy that applies the signed policy's request/body limits before forwarding to a statically configured origin.
- Tests using synthetic identities, a fake Kubo adapter and HTTP servers bound only to loopback.
- A focused GitHub Actions workflow for the CDD unit and gateway suites.

## Security boundaries and limitations

- The HTTP gateway is an experimental synchronous laboratory proxy, not a production-grade ingress service.
- Do not expose the gateway to the public internet or use it as the only protection for a real website.
- The configured origin URL is operator-controlled; the client cannot choose an upstream destination. The gateway does not configure firewalls, secure DNS, or prevent direct origin bypass. The origin must be separately firewalled or require authenticated gateway-to-origin connections before deployment.
- The limiter keys requests by the TCP peer IP and does not trust client-provided `X-Forwarded-For` or identity headers. It is process-local; distributed gateways do not share quotas.
- Rate limiting is not proof that a request is a bot. It is a simple abuse-control primitive and may cause false positives.
- Kubo adapter unit tests use a fake Kubo object. A real Kubo integration test is still required.
- This does not implement P2P service discovery, traffic steering, DNS/Anycast, a public contract, upstream volumetric DDoS filtering, or a distributed/global quota coordinator.
- A CID identifies content; it does not by itself authenticate the publisher or guarantee that a policy is safe. The signature and trusted-issuer configuration are still mandatory.
- Do not publish private keys, credentials, access tokens or secrets to IPFS.

## Policy lifecycle

1. An authorized issuer signs a canonical JSON policy with its existing Node Core OS Ed25519 identity.
2. The publisher writes those exact signed bytes to Kubo. Kubo returns the actual CID; the application must never invent one.
3. A gateway retrieves the bytes by CID and checks the schema, issuer allowlist, signature, freshness and sequence before using the policy.
4. The gateway binds the signed `service_id` and `origin_id` to an operator-configured upstream. It does not accept an upstream URL from a request.
5. Policy cache lifetime, revocation freshness, rollback persistence and outage behavior must be specified before production deployment.

## Test commands

From the repository root:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_cdd_security.py' -v
python -m unittest discover -s tests -p 'test_cdd_gateway.py' -v
```

The dedicated GitHub Actions workflow runs both suites on relevant pull requests, pushes to `main`, and manual dispatches. Passing these suites demonstrates only the behavior they exercise; it does not prove production readiness.

## Next implementation stages

1. Add a real Kubo-backed test using an isolated temporary Kubo repository/daemon in CI where supported.
2. Add explicit origin-bypass tests and deployment guidance for firewall rules or gateway-to-origin mTLS.
3. Run several loopback gateways and test failure removal, failover and bounded load distribution.
4. Define cross-node rate-limit coordination and behavior during partition.
5. Integrate authenticated P2P discovery with existing Node Core OS networking interfaces.
6. Evaluate a public contract only after choosing the chain, governance and failure model.
7. Compare against a conventional reverse proxy/WAF baseline under identical bounded laboratory conditions.

Every stage must provide code, tests and evidence before its status is described as verified. No public target or external attack traffic is used by these tests.
