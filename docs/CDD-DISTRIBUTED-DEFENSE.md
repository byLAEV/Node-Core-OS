# Node Core OS byLAEV — CID Distributed Defense (CDD)

**Version:** experimental MVP 0.1  
**Status:** initial local security primitives; not a production gateway or DDoS mitigation service.

## Goal

CDD is an incremental architecture for protecting existing Web2 domains, HTTP services and APIs with multiple ingress nodes, signed security policies, bot-abuse controls and optional P2P discovery. Protected websites and origins do not need to migrate to IPFS.

## What this first implementation contains

- A signed, versioned policy format using the repository's existing Ed25519 node identity.
- Strict policy validation, issuer allowlisting, expiry checks and monotonic sequence/anti-rollback validation.
- A bounded in-process sliding-window request limiter suitable for local unit tests and as a primitive for a future gateway.
- Automated tests using synthetic identities and deterministic timestamps.

## What this first implementation does not contain

- An HTTP reverse proxy or production ingress gateway.
- Kubo publication/retrieval or automatic CID generation for policy bytes.
- A distributed/global rate-limit coordinator.
- P2P service discovery for Web2 domains.
- A public smart contract or blockchain adapter.
- DNS/Anycast/traffic steering, upstream volumetric DDoS filtering, origin firewall automation, or production deployment.
- A claim that malicious intent can be determined from a single request or that a website cannot be taken offline.

## Policy lifecycle

1. An authorized policy issuer creates the policy body and signs its canonical JSON representation with the existing Node Core OS Ed25519 identity.
2. A verifier checks the exact schema, issuer allowlist, key-to-node-ID binding, signature, issue/expiry times, and monotonic sequence.
3. The exact signed policy bytes may later be published to Kubo. Kubo must return the CID for those bytes; this module deliberately does not fabricate a CID.
4. A gateway integration must verify the bytes and signature before applying the policy. A CID establishes content addressing/integrity, not publisher authority or policy safety.
5. Nodes may cache verified policies only until their defined expiry. Revocation freshness and behavior when trust data is unavailable must be specified before production use.

## Policy limits

The MVP schema bounds requests, time window and body size to prevent accidental unbounded configuration. The local limiter keys counters by the supplied client identity and route. Callers must authenticate or authorize the client identifier; a user-controlled header alone is not a trusted identity.

The limiter is process-local. Multiple gateways do not share quotas merely because they load the same CID policy. Cross-node coordination and safe behavior when that coordinator fails are separate future work.

## Required security properties

- Unknown issuer, invalid signature, unknown fields, malformed timestamps, future-issued or expired policy: reject.
- Sequence less than or equal to the last accepted sequence: reject.
- Invalid or excessive limits: reject at policy creation and verification.
- Rate-limit tracking storage is bounded; when full, new client keys are denied rather than allocating unbounded memory.
- No secret key material is included in a policy.
- Tests bind only to synthetic identities and do not contact public websites or generate external traffic.

## Test command

From the repository root, using the project's declared dependencies:

\`\`\`bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_cdd_security.py' -v
\`\`\`

The dedicated GitHub Actions workflow runs these tests on relevant pull requests and manual dispatches. The existing repository CI also compiles the module and runs the broader unit-test suite.

## Next implementation stages

1. Integrate the signed policy with a local HTTP gateway and enforce request/body limits.
2. Add Kubo-backed publication/retrieval of the exact signed bytes and verify the returned CID.
3. Add bounded multi-gateway failover tests and explicit origin-bypass protection.
4. Integrate authenticated bot signals and define false-positive measurements.
5. Add P2P discovery using existing Node Core OS networking interfaces.
6. Evaluate a public contract only after choosing its chain, governance and failure model.
7. Compare against a conventional reverse proxy/WAF baseline under identical bounded laboratory conditions.

Each stage requires code, tests and evidence before its status can be changed from proposed to implemented or verified.
