# Service Specification — IPFS Content Integrity

- **Product ID:** `CERT-07`
- **Certificate profile:** `ipfs-content-integrity`
- **Version:** `0.1.0-draft` | **Status:** `proposed`
- **Economic policy:** `pending-consensus`

## Purpose and method

Use authorized test fixtures to verify CID/content correspondence, retrieval behavior, missing-block handling, retention/pinning claims, and safe handling of untrusted content. Define whether the test concerns local storage, a particular Kubo node, or a wider IPFS topology.

## Deliverables

Fixture identifiers and hashes, retrieval/integrity outcomes, topology and test period, availability observations, and limitations.

## Minimum acceptance criteria

- Scope, authorization, fixture data, software version, and topology are recorded.
- Positive, negative, missing-content, and mismatch cases are documented where applicable.
- Integrity is reported separately from content safety, privacy, and legality.
- Availability and retention claims are bounded by the tested period and topology.
- Private content is not published to public IPFS without explicit authorization.

## Evidence record

Preserve work-order reference, target scope, CID, expected fixture hash, observed result, Kubo/client version, timestamps, provider identity, relevant logs, and integrity hashes. Do not place confidential payloads in public evidence.

## Current testing boundary

The certificate profile is recognized, but certificate-envelope tests do not establish Kubo/IPFS retrieval, pinning, retention, or malicious-content detection.

## Required next tests

Add Kubo integration tests for correct and mismatched content, missing blocks, retrieval failure, pin/retention claims, and safe content handling.

## Failures, disputes, and economics

Record incomplete retrieval, ambiguous results, environment failures, and retest requests. Failure is not automatically fraud. Prices, fees, provider/verifier shares, and reward formulas remain `pending-consensus`; this specification does not authorize payment.
