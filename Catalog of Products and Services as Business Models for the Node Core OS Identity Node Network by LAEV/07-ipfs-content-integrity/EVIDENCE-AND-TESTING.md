# Evidence and Testing — IPFS Content Integrity

**Profile:** `ipfs-content-integrity`  
**Evidence status:** Product-specific effectiveness testing is not established by the certificate-format tests alone.

## Existing evidence boundary

The profile is recognized, but certificate-envelope tests do not establish Kubo/IPFS retrieval, pinning, retention, or malicious-content detection.

See the [catalog-wide test and evidence matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md), [certificate unit tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_node_identity_certificate.py), and the relevant [GitHub Actions conformance workflow](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/node-identity-certificate.yml). A profile being accepted by the certificate format is not proof that the corresponding security control works. A workflow definition is not proof of a successful run; record a completed run for the exact commit.

## Test plan

1. Record the exact commit, product version, configuration, environment, and expected behavior.
2. Run authorized positive and negative scenarios relevant to this product.
3. Test boundaries, partial failure, recovery, and ambiguous results where applicable.
4. Verify evidence integrity, timestamps, provenance, and reproducibility.
5. Review scope authorization, safety limits, privacy, and secret handling.
6. Record pass/fail status, failure details, limitations, and the exact CI run URL.

## Required evidence fields

Record test ID, work-order and authorization reference, target scope, commit SHA, environment, configuration, tool/dependency versions, reproducible command or procedure, expected and observed results, artifact hashes or signed references, timestamp, operator/reviewer, conflicts of interest, limitations, and CI run URL.

## Required next tests

Add Kubo integration tests for correct/mismatched content, missing blocks, retrieval failures, pin/retention claims, and safe content handling.

## Publication and safety rules

- Do not label a test as passed without a successful recorded run for the relevant code.
- Do not claim production readiness from a synthetic or isolated test alone.
- Keep sensitive customer evidence access-controlled; do not publish secrets, private keys, or unnecessary personal data.
- Report failures and untested controls rather than silently omitting them.
- Offensive testing requires explicit authorization and defined stop conditions.

## Economic status

Prices, fees, provider/verifier shares, and distribution formulas remain `pending-consensus`. This testing guide does not authorize payments or guarantee income.
