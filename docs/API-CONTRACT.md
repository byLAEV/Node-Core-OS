# Node Core OS API Contract

## Status

**Status: proposed contract, not an implemented public API.**

This document defines the compatibility and security principles that must be satisfied before Node Core OS advertises a stable API. It does not claim that the endpoints or SDKs described here already exist.

## Purpose

Node Core OS should expose a stable, documented interface so external applications and protocols can request capabilities without depending on internal implementation details or duplicating the core.

The API is a boundary between the Node and a client application. It is not permission for a client to access every local file, Kubo administrative endpoint, identity record, or secret.

## Design principles

1. **Explicit requests:** state-changing operations must originate from an authorized request.
2. **Least privilege:** clients receive only the capabilities and data required for their declared purpose.
3. **Local-first storage:** local storage and Kubo/IPFS are separate backends with explicit behavior.
4. **Privacy by default:** storing content does not authorize sharing, propagation, or publication.
5. **Stable contracts:** public inputs, outputs, errors, and compatibility guarantees must be documented and tested.
6. **No secret leakage:** private keys, tokens, credentials, and private configuration must not be returned by ordinary API responses or written to logs.
7. **Versioning:** incompatible changes require a new major API version or a documented migration plan.
8. **Observable behavior:** errors and status results must be structured and documented.
9. **Minimal dependencies:** the first implementation should use the repository's existing runtime and dependencies where practical.
10. **Testability:** each implemented operation must have tests for success, invalid input, denied access, missing content, and backend failure where applicable.

## Capability groups

These groups are proposed. A group becomes supported only after implementation, tests, and reference documentation exist.

### Health and diagnostics

Read-only status about the Node process and supported services. Diagnostics must redact secrets and private user data.

### Storage

- Store a local resource.
- Retrieve a resource the caller is authorized to access.
- List metadata only within an explicitly authorized scope.
- Delete local data only through an explicit operation with documented consequences.

### Content and IPFS

- Add content and return its CID.
- Retrieve content by CID subject to configured policy.
- Pin or unpin content through explicit requests.
- Return content metadata and operation status.

Pinning content does not guarantee that the content is available from every peer. A CID identifies content; it does not establish the truth of a claim about that content.

### Identity and evidence

Future interfaces may manage identifiers, evidence records, attestations, and corroboration. These interfaces must define ownership, provenance, validity, revocation, privacy, and authorization before being treated as stable.

### Protocols

Protocol integrations must declare requested capabilities, input/output schemas, permissions, lifecycle, and failure behavior. An application must not gain broader access merely because it is installed.

## Request and response requirements

Every state-changing request must have:

- a documented operation name and API version;
- validated input with size and type limits;
- an authenticated or otherwise explicitly authorized caller;
- an authorization check for the specific capability and resource;
- a clear success or failure result;
- a traceable operation identifier where appropriate;
- tests demonstrating expected behavior.

Responses must not disclose host paths, secrets, private records, or internal configuration unless explicitly required and authorized.

## Error model

Implementations should use a consistent structured error shape, for example:

```json
{
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "A required field is missing",
    "request_id": "example-request-id"
  }
}
```

The values above are illustrative, not a currently implemented response schema. Error messages must not reveal credentials, secret paths, or sensitive internal details.

## Authentication and authorization

Before a network-accessible API is enabled, the implementation must define:

- how a client is identified;
- how credentials are issued, stored, rotated, and revoked;
- which capabilities each client may use;
- how local-only operation is protected from remote access;
- how requests are audited without logging sensitive payloads;
- how replay, brute force, and unauthorized access are mitigated.

Do not expose Kubo's administrative RPC directly as the Node Core application API. Node Core should mediate access through its own capability and authorization boundary.

## Versioning and compatibility

- Public API versions must be explicit.
- Non-breaking additions may be made within a supported major version.
- Removing fields, changing field meaning, or changing authorization behavior incompatibly requires a major version or migration.
- Deprecations must be announced in release notes and kept for a documented transition period where feasible.
- SDK releases must state the API versions they support.

## Acceptance gate for declaring an API stable

A capability may be labeled **stable** only when all applicable checks pass:

1. Implementation exists in the repository.
2. Input and output schemas are documented.
3. Authorization and privacy behavior are tested.
4. Success and failure tests pass in CI.
5. A runnable example is provided.
6. Compatibility and versioning are documented.
7. No credentials or private user data are exposed by tests, examples, or logs.

Until then, label the interface **proposed**, **experimental**, or **in development** as appropriate.

## Contribution workflow

Community members can propose an API or SDK by opening an issue with:

- problem and intended consumers;
- proposed operation names and schemas;
- authorization and privacy implications;
- failure modes;
- compatibility impact;
- test plan;
- minimal runnable example.

Implementation should be submitted through a reviewed pull request following [CONTRIBUTING.md](../CONTRIBUTING.md).
