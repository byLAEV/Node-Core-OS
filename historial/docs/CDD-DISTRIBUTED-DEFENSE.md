# Node Core OS byLAEV — CID Distributed Defense (CDD)

**Version:** experimental MVP 0.3  
**Status:** signed policies, a local HTTP gateway, and a loopback multi-gateway router are under test. Not a production edge or DDoS mitigation service.

## Goal

CDD is an incremental architecture for protecting existing Web2 domains, HTTP services and APIs with multiple ingress nodes, signed security policies, request-abuse controls and future P2P discovery. Protected websites and origins do not need to migrate to IPFS.

## Implemented components

- Signed, versioned policy creation and verification using the repository's existing Ed25519 node identity.
- Strict policy validation, issuer allowlisting, key-to-node-ID binding, expiry checks and anti-rollback sequence.
- Bounded in-process sliding-window request limiting.
- Kubo adapter helpers that publish the exact signed JSON policy bytes using `KuboManager.add_file(pin=True)` and load them using `KuboManager.cat(cid)`, then verify the signature.
- Laboratory HTTP reverse proxy that applies the signed policy's request/body limits before forwarding to a statically configured origin.
- Optional gateway-to-origin shared-token authentication for the lab. The origin must independently enforce this token; merely configuring it at the gateway does not protect an origin that accepts unauthenticated direct traffic.
- Loopback multi-gateway router with round-robin selection and GET/HEAD failover after transport errors or 502/503/504 responses. Non-idempotent methods are not automatically retried.
- Tests use synthetic identities, a fake Kubo adapter and local HTTP servers.
- Three-gateway loopback integration measures round-robin distribution, GET failover after deliberately stopping one gateway, response latency and availability, direct-origin rejection, signed CID-policy loading/tamper rejection, and expired-policy rejection.
- Shared-quota integration injects the same in-process limiter into three independent HTTP gateway listeners. This validates the shared quota interface but is not a cross-process or cross-machine coordinator.
- A focused GitHub Actions workflow runs CDD primitives, gateway and router tests.

## Security boundaries and limitations

- Do not expose the experimental gateway or router directly to the public Internet.
- The router only distributes requests among statically configured gateways. It does not implement public DNS/Anycast, P2P discovery, dynamic health registration, geographic routing, or global capacity management.
- Failover is tested only with local synthetic services. It does not prove production availability, DDoS resistance or that every request will survive a real node failure.
- Round-robin is not a global rate-limit coordinator. Each gateway has local counters, and this lab router does not establish a trusted end-user identity across hops. A production design must define authenticated proxy hops and a trustworthy client-identity chain.
- The optional shared origin token is a laboratory control, not mutual TLS. Production should use network ACL/private origin connectivity and preferably authenticated gateway-to-origin transport such as mTLS. Rotate and protect secrets; never publish them to IPFS.
- The origin bypass test demonstrates only that a local test origin rejects a request without the configured token. It does not configure firewalls or protect any real domain.
- Kubo adapter unit tests use a fake Kubo object. Real Kubo daemon interoperability remains a separate test.
- A CID identifies content; it does not itself authenticate the publisher or guarantee a policy is safe. Signatures and trusted-issuer configuration are mandatory.
- Do not publish private keys, credentials, access tokens or secrets to IPFS.
- Volumetric attacks that saturate upstream links require upstream provider mitigation and sufficient ingress capacity; distributing application gateways alone cannot solve that.

## Policy lifecycle

1. An authorized issuer signs a canonical JSON policy with its existing Node Core OS Ed25519 identity.
2. The publisher writes those exact signed bytes to Kubo. Kubo returns the actual CID; the application must never invent one.
3. A gateway retrieves the bytes by CID and checks the schema, issuer allowlist, signature, freshness and sequence before using the policy.
4. The gateway binds the signed `service_id` and `origin_id` to an operator-configured upstream. A client request cannot choose an upstream URL.
5. Policy cache lifetime, revocation freshness, rollback persistence and outage behavior must be specified before production deployment.

## Test commands

From the repository root:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_cdd_security.py' -v
python -m unittest discover -s tests -p 'test_cdd_gateway.py' -v
python -m unittest discover -s tests -p 'test_cdd_router.py' -v
python -m unittest discover -s tests -p 'test_cdd_integration.py' -v
```

The dedicated GitHub Actions workflow runs the three suites on relevant pull requests, pushes to `main`, and manual dispatch. Passing them demonstrates only the behaviors they exercise; it does not prove production readiness.

## Next implementation stages

1. Add a real Kubo-backed test using an isolated temporary Kubo repository/daemon in CI where supported.
2. Replace the shared lab origin token with private origin networking and gateway-to-origin mTLS guidance/tests.
3. Define authenticated client identity propagation and cross-node rate-limit coordination.
4. Integrate authenticated P2P discovery with existing Node Core OS networking interfaces.
5. Evaluate a public contract only after choosing the chain, governance and failure model.
6. Implement a durable, authenticated cross-process quota coordinator with explicit timeout/fail-closed behavior and test coordinator outage.
7. Run the three-gateway integration suite repeatedly and retain machine-readable metrics artifacts.
8. Compare against a conventional reverse proxy/WAF baseline under identical bounded laboratory conditions.

Every stage must provide code, tests and evidence before its status is described as verified. No public target or external attack traffic is used by these tests.
