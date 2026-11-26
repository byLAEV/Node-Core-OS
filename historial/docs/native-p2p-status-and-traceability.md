# Native P2P discovery: status, safety, and traceability

**Status:** design contract for implementation and review. This document does not claim that every capability described below is implemented.

**Related work:** [LAN identity handshake #119](https://github.com/byLAEV/Node-Core-OS/issues/119), [worldwide discovery #120](https://github.com/byLAEV/Node-Core-OS/issues/120).

## 1. User-facing promise

Node Core OS has two independent native P2P discovery scopes:

1. **Local / LAN:** identify nodes in the same local environment or local network.
2. **Worldwide / WAN:** discover nodes across separate networks through real, configured internet-facing infrastructure.

Localhost is a loopback-only endpoint for processes on the same device. It is not a LAN endpoint. LAN multicast does not cross routers and must never be described as worldwide discovery. Kubo/IPFS status is a separate subsystem and must not be used as proof that native P2P is online.

A clean installation should use safe defaults and start what it can without requiring users to supply hostnames or ports. If an infrastructure dependency is missing or unavailable, the interface must say so plainly rather than displaying a false success state.

## 2. State vocabulary

Do not collapse these states into a single "connected" flag:

| State | Meaning | Does it imply trust? |
| --- | --- | --- |
| **Discovered** | A bounded, fresh announcement or directory record was received. | No |
| **Identity authenticated** | Cryptographic proof tied the remote public key to the claimed node ID. | No |
| **Trusted / authorized** | Local policy explicitly grants the peer defined permissions. | Yes, only for the stated scope |
| **Connected** | A live transport/session exists and passes the protocol's authentication requirements. | Not by itself |
| **Application authorized** | The peer is allowed to invoke a particular application operation. | Only for that operation |

A signed announcement proves possession of the announcement signing key for that message; it does not prove that the advertised endpoint is reachable or that a session is open. A valid TLS session is not a substitute for application-level authorization.

## 3. Per-scope status and diagnostics

Each discovery scope should report these fields (or documented equivalents):

- `state`: `not_configured`, `starting`, `active`, `degraded`, or `unavailable`.
- `scope`: `localhost`, `lan`, or `wan`.
- `last_success_at`: timestamp in UTC, or `null` if never successful.
- `last_error`: concise, actionable error or `null`.
- `next_retry_at` or retry/backoff state when automatic retry is active.
- `observed_peer_count`: only records currently valid under the documented TTL and validation rules.
- `infrastructure`: protocol/provider name and a non-secret endpoint identifier where relevant.
- `request_id`: where an operation has a request/correlation identifier.

Rules:
- `active` means the specific discovery mechanism is running and has passed its local startup checks; it must not imply that any remote peers were found.
- `observed_peer_count > 0` means announcements/records were observed, not that sessions are authenticated.
- `wan.state = active` requires a configured real WAN mechanism and a successful operational check. A hard-coded boolean or successful LAN multicast startup is not evidence.
- Errors should explain what the user can do next. Avoid raw tracebacks in the normal menu; preserve detailed diagnostics in an appropriate log.
- Never log private keys, authentication tokens, or secret configuration values.

## 4. Security invariants

1. Discovery must not add peers to the trust store.
2. Authentication and authorization must remain separate.
3. Privileged application operations require the existing explicit authorization policy until a reviewed replacement policy is accepted.
4. Revocation must invalidate future authorization and close relevant active sessions; tests must cover races with new handshakes.
5. Do not advertise an endpoint until a listener is bound and its actual port is known. Port `0` means identity visible with no advertised inbound endpoint.
6. Do not bind to all interfaces by default without a documented threat model and explicit security review.
7. Bound message size, peer registry size, record TTL, socket timeouts, retry/backoff, and concurrent work.
8. Invalid signatures, malformed records, expired records, and protocol-version mismatches must fail closed.
9. Discovery failure must not prevent the local core from starting.
10. No Kubo/IPFS requirement and no root/sudo requirement for native P2P discovery.

## 5. User experience

The main menu should retain its established layout and add only a concise native-network summary. The dedicated Network / Nodes menu should make it easy to:

- see Local/LAN and Worldwide/WAN status separately;
- refresh status and see the last update time;
- list discovered identities separately from trusted peers and active sessions;
- understand why a scope is unavailable and whether automatic retry is running;
- inspect the node ID and public certificate fingerprint safely;
- revoke trust with an explicit confirmation.

Avoid vague labels such as `ONLINE` when only a discovery socket is running. Prefer messages like:

- `LAN discovery: ACTIVE — no valid announcements observed yet`
- `LAN discovery: DEGRADED — multicast unavailable; retrying`
- `WAN discovery: NOT CONFIGURED — no rendezvous/bootstrap service is configured`
- `Identity: DISCOVERED — not authenticated; not trusted`
- `Session: CONNECTED — peer authenticated; authorization scope: status-only`

These are examples of vocabulary, not assertions about the current runtime state.

## 6. Traceability required for every implementation PR

Every PR affecting discovery, authentication, authorization, or the network UI must include:

1. The issue(s) and user-facing behavior it addresses.
2. A short design decision record: chosen approach, alternatives considered, security implications, and operational dependencies.
3. Files changed and the reason for each change.
4. Tests added or modified, with the specific behavior each test proves.
5. Exact validation actually executed: commands, environment/user context, results, and links to CI runs.
6. Known limitations and rollback considerations.
7. Explicit statement that no release was published, unless a release was actually created.

Do not write "tested" for a test that was merely added or inspected. Distinguish unit tests, simulated tests, local multi-process tests, LAN tests, and real WAN end-to-end tests.

## 7. Minimum validation matrix

| Scenario | Expected result |
| --- | --- |
| Fresh install, no Kubo/IPFS | Local core starts; native status is available or explains its failure |
| Multicast unavailable | LAN discovery reports degraded/unavailable and retries safely |
| Valid signed announcement | Identity appears as discovered only |
| Invalid signature or expired announcement | Record is rejected and not shown as valid |
| No trusted peers configured | No privileged session starts; no implicit trust is created |
| Trusted peer handshake | Identity and authorization are verified independently |
| Revocation during active session | Relevant session is closed and reconnect is denied |
| WAN service not configured | WAN clearly says not configured, never active |
| WAN service outage | LAN continues independently; WAN shows failure and retry details |
| Two nodes on separate networks | Real integration test demonstrates WAN discovery; mocks alone do not satisfy this case |
| Port conflict / unavailable interface | Useful error is shown; no incorrect endpoint is advertised |
| Non-root Linux user | Install, run, status, and shutdown work without sudo |

## 8. Delivery gate

Do not merge a security-sensitive handshake or publish a release based only on a successful syntax check or mocked unit tests. Require the relevant unit suite, installer/package checks, GitHub Actions, and the integration tests described in the linked issues. Where a real network test cannot run in CI, record it as pending and do not represent that capability as verified.
