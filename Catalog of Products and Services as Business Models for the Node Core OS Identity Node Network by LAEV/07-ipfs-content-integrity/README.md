# 7. IPFS Content Integrity

**Profile:** `ipfs-content-integrity` | **Catalog status:** Proposed | **Economic policy:** Pending consensus

## Product purpose

Assess content-address integrity, retrieval behavior, retention claims, and safe handling of untrusted content in an authorized local/IPFS deployment, including Kubo where in scope.

## Assessment objectives

- Verify content/CID correspondence for defined test fixtures.
- Test retrieval failures, missing blocks, and integrity mismatch handling where supported.
- Review pinning and retention claims against the tested topology and period.
- Separate integrity verification from content safety, privacy, and legality.

## Deliverables

Content identifiers and fixture hashes, retrieval/integrity results, availability observations, retention scope, limitations, and remediation guidance.

## Acceptance principles

Use authorized non-sensitive fixtures; report CID integrity separately from content safety; bound availability claims by test period and topology. Do not publish private content to public IPFS without explicit authorization.

## Current testing boundary

The profile identifier exists. Certificate-envelope tests do not establish Kubo/IPFS retrieval, pinning, retention, or malicious-content detection. Dedicated integration tests are required.

See [service specification](./SERVICE-SPECIFICATION.md) and the [catalog test matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md).
