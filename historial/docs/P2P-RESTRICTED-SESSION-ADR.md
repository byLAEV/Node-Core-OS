# P2P Restricted Identity Session — Architecture Decision Record

**Status:** Design approved for implementation planning; implementation not yet accepted.
**Scope:** Issue #119 — native LAN discovery and identity authentication without automatic application trust.

## 1. Current verified architecture

The repository already has separate building blocks:

- \`NodeDiscoveryService\` receives signed multicast announcements and records ephemeral discoveries. It does not authorize peers.
- \`NodeTLSTransport\` creates TLS 1.3 certificates bound to the Ed25519 node identity. Its current client/server contexts require explicitly pinned peer certificates.
- \`PeerAuthenticator\` performs nonce-bound mutual Ed25519 HELLO/AUTH authentication.
- \`AuthenticatedPeerSession\` binds a peer HELLO to the TLS peer certificate and expected node ID.
- \`NodePeerService\` requires the explicit trusted-certificate allowlist before it registers application sessions.
- \`PeerTrustStore\` persists only explicitly trusted or revoked peers.

The missing component is a separate, bounded, read-only session for a discovered identity that has not been explicitly trusted.

## 2. Security invariant

**Identity authentication is not authorization.**

A peer may be discovered and cryptographically authenticated without being inserted into \`PeerTrustStore\`, without becoming an application peer, and without gaining access to MESSAGE, PEERS, secure messaging, relaying, storage, execution, or application callbacks.

The existing \`NodePeerService\` trusted application path and its revocation behavior must remain unchanged.

## 3. Certificate bootstrap decision

The current TLS contexts cannot authenticate a previously unknown self-signed certificate: they require a preconfigured pinned certificate. Removing that check or setting an unauthenticated TLS mode on the existing application listener is prohibited.

The restricted listener will use a **discovery-scoped certificate candidate set**, separate from the durable trust allowlist:

1. Extend the signed discovery announcement with a bounded encoding of the node's existing self-signed TLS certificate (or an equivalent bounded certificate record). The announcement signature must cover the certificate bytes/fingerprint as well as node ID, public key, address, port, timestamp, and protocol version.
2. Validate the certificate before caching it: Ed25519 key type, self-signature, validity interval, node identity SAN, and public key-derived node ID must all match the signed announcement.
3. Keep the certificate in an ephemeral discovery cache with the same bounded peer count and TTL policy. Never write it to \`PeerTrustStore\` merely because it was discovered.
4. Build a fresh restricted TLS 1.3 context per accepted connection from the current, non-expired discovery certificate candidates. The client context uses the exact discovered certificate for the selected node. The server context uses the current discovered candidates for client-certificate verification.
5. After TLS, run the existing nonce-bound \`PeerAuthenticator\` / \`AuthenticatedPeerSession\` logic and compare the TLS certificate fingerprint, certificate public key, HELLO public key, and node ID. A mismatch closes the connection.
6. Treat the discovered certificate as a **transport authentication candidate only**, never as an authorization grant. A malicious node may advertise its own valid identity; that makes it discoverable, not trusted.

This preserves mutual TLS 1.3 and the existing Ed25519 identity binding without accepting arbitrary certificates or weakening the trusted application listener.

## 4. Restricted service boundary

Implement a separate service and session type, not a mode flag on \`NodePeerService\`:

- \`RestrictedPeerService\`: separate listener, certificate-candidate provider, bounded worker pool, connection lifecycle, and revocation checks.
- \`RestrictedPeerSession\`: TLS + existing mutual identity handshake + one narrowly defined identity/status protocol.
- Do not import or call \`send_application_message\`, \`receive_application_message\`, secure-messaging functions, application handlers, or peer-list handlers from the restricted session module.
- Do not share the application message dispatcher with the restricted listener.

### Allowed protocol

Only one request/response family is allowed:

- \`IDENTITY_STATUS_REQUEST\`: exact fields \`version\`, \`type\`, \`request_id\`.
- \`IDENTITY_STATUS_RESPONSE\`: exact fields \`version\`, \`type\`, \`request_id\`, \`node_id\`, \`protocol_version\`, \`availability\`.

The response fields must be enumerated, validated, and bounded. Do not return filesystem paths, peer lists, IPFS/Kubo data, local usernames, hostnames, arbitrary metadata, or application state. Unknown message types, extra fields, duplicate JSON keys, invalid request IDs, invalid lengths, or malformed UTF-8 close the connection. No fallback to the application protocol is permitted.

## 5. State model

The UI and runtime must distinguish:

1. \`discovered\` — a fresh signed LAN announcement was validated.
2. \`identity_authenticated\` — TLS and mutual nonce-bound Ed25519 proof succeeded.
3. \`trusted\` — an explicit operator action added the exact peer certificate to \`PeerTrustStore\`.
4. \`revoked\` — the trust record is revoked; restricted and application sessions are denied.
5. \`application_session_active\` — the existing trusted application session is active.

Transitions are explicit. \`identity_authenticated\` must never auto-transition to \`trusted\`. A restricted status session does not mean \`application_session_active\`.

For an unknown peer, the restricted service may permit read-only status. For a trusted peer, use the existing application path. A revoked peer is denied on connection and before every status request.

## 6. Resource and failure controls

The restricted service must enforce:

- A fixed maximum number of worker threads and accepted sockets; reject excess work without spawning unbounded threads.
- Bounded handshake and frame sizes; separate small limits for identity/status frames.
- Connect, TLS handshake, authentication, read, and idle timeouts.
- Per-source rate limiting using the observed socket address, never caller-provided forwarding fields.
- A bounded ephemeral discovery-certificate cache with expiry and deterministic eviction.
- Socket close on every malformed message, timeout, authentication failure, revocation, or unexpected exception.
- Synchronous session termination when a peer is revoked.
- No automatic trust-store writes, no Kubo dependency, no root/sudo.

## 7. Implementation sequence

1. Add certificate material to signed discovery announcements and validate certificate-to-key/node-ID binding.
2. Add discovery-cache accessors for current certificate candidates, with expiry and bounded size.
3. Add restricted TLS context builders that require peer certificates from the discovery candidate set. Do not change existing application TLS context behavior.
4. Add \`RestrictedPeerSession\` with exact schemas, mutual authentication, status-only exchange, and fail-closed framing.
5. Add \`RestrictedPeerService\` with bounded concurrency, rate limits, timeouts, lifecycle, and revocation integration.
6. Add UI/runtime state projection without conflating authentication and trust.
7. Add unit tests, then two independent local processes, then physical LAN devices.

## 8. Required acceptance evidence

- Two independent processes with separate identity stores discover one another and complete mutual TLS 1.3 + Ed25519 identity authentication.
- A discovered unknown identity can request only the bounded identity/status response.
- MESSAGE, PEERS, secure-message, relay, unknown types, duplicate JSON keys, and extra fields close the restricted socket and never invoke application handlers.
- Invalid certificate signature, invalid validity, wrong SAN, certificate/key/node-ID mismatch, invalid Ed25519 signature, replay, oversized frame, timeout, and revoked identity are rejected.
- A certificate appearing in discovery never changes the durable trust store.
- Revocation terminates active restricted sessions synchronously and prevents reconnect/status.
- Existing trusted application sessions, peer revocation, installer E2E, and package tests remain green.
- Physical LAN acceptance is recorded separately; multicast-unavailable CI may skip gracefully but cannot be reported as LAN acceptance.

## 9. Explicit non-goals

No trust-on-first-use in the application allowlist, no plaintext identity handshake on LAN, no anonymous application access, no P2P Contracts activation, no Kubo dependency, no global network exposure, and no claims of physical-LAN acceptance from loopback CI.
