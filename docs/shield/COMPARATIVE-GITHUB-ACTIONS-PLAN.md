# Shield Comparative Security Campaign — GitHub Actions Plan

**Status:** test plan and CI orchestration contract. This document is not evidence that the full comparative campaign has run.

## Goal

Compare two deployments against the same synthetic web application and data set:
- **A — Conventional baseline:** standard TLS, maintained reverse proxy/WAF, application authentication, request limits and database least privilege.
- **B — Baseline + Node Core OS:** exactly the same A controls, plus Node Core OS identity, signed threat reports, receiver-side quorum policy, revocation and a Shield enforcement adapter.

Keeping the baseline controls identical isolates the incremental contribution of Node Core OS. A second comparison may compare recommended complete configurations, but must not mix those results with the incremental comparison.

## Safety boundaries

- Run only on ephemeral GitHub-hosted runners and loopback/private container networks.
- Use a deliberately vulnerable application and disposable synthetic database with no production secrets or personal data.
- Do not scan or attack public domains, arbitrary IP addresses or third-party services.
- Keep load tests bounded; no volumetric DDoS traffic. Network saturation cannot be meaningfully or safely tested on shared CI runners.
- All test jobs run as the ordinary runner user; never use sudo or root execution in project scripts.
- Pin container images by digest before treating a run as a release-grade benchmark. Store image digests and tool versions in each report.
- An assertion failure, missing report, skipped test or incomplete run must never be represented as a pass.

## Campaign stages

### Stage 0 — Existing security regression (implemented)

Run existing tests for Ed25519 identity/signatures, TLS peer identity, Shield support evidence and quorum, signed identity credentials, local web lab, API abuse/rate limiting, three-node loopback TLS alert acceptance, and revocation/replay/expiry/tampering/partition recovery where implemented. These tests verify the named code paths; they are not proof of general web attack resistance.

### Stage 1 — Reproducible professional web fixture (next implementation)

Use a pinned OWASP Juice Shop release or another explicitly vulnerable fixture in a disposable container network. Place a maintained OWASP Core Rule Set (CRS) WAF in front of it. Add a synthetic database seeded only with fake records. Save container image digests, CRS version, app version and configuration. First prove the baseline fixture works and is isolated; do not expose public ports.

### Stage 2 — Paired A/B deployments

Start two identical fixtures. A uses conventional TLS/reverse proxy/WAF. B uses the same TLS/reverse proxy/WAF and application, with an actual Node Core OS Shield enforcement adapter in the request path. The adapter must consume verified identity/alert evidence and enforce an explicit policy. A unit test that merely creates a credential or records an alert does not count as web enforcement. If the adapter is not integrated, the comparative job must mark B as NOT_IMPLEMENTED and must not manufacture an A/B result.

### Stage 3 — Attack classes

Run identical deterministic cases against A and B: benign controls; SQL injection and XSS against the safe fixture; malformed HTTP, oversized headers/body and invalid content types; authentication/API abuse and bounded brute-force simulation; replayed, expired, altered and unsigned alert records; unauthorized, revoked, duplicate and colluding reporter identities; legitimate clients during quarantine; and fail-open/fail-closed behavior when nodes are unreachable. Correlate edge logs with application-side request IDs so an edge 403 is not confused with prevention inside the app.

### Stage 4 — Bounded performance and resilience

Use repeatable concurrency levels with strict time/request budgets. Record requests per second, p50/p95/p99 latency, HTTP status distribution, application errors, CPU and peak memory per container, alert propagation/quorum decision latency, false-positive rate on benign requests, and recovery time after false quarantine or node reconnection. Repeat runs, alternate A/B order and report median/spread. Shared CI runners are noisy; results are comparative signals, not production capacity guarantees.

Do not perform volumetric DDoS tests on shared GitHub runners. Test bounded rate limiting and resource exhaustion only. DDoS resilience requires a separately authorized isolated network with known capacity or an upstream provider test.

### Stage 5 — Acceptance and reporting

Generate machine-readable report.json and a Markdown summary containing commit SHA, workflow run ID, runner OS, Python/tool versions and image digests; scenario counts; A/B results; false positives, missed attacks, latency and resource metrics; missing coverage and limitations.

Acceptance criteria:
1. All required safety controls and integrity checks pass.
2. No attack case is silently skipped.
3. A and B receive identical test inputs.
4. The Shield adapter is confirmed in-path for B.
5. Benign request blocks are counted and explained.
6. Performance results include repeated runs and environment metadata.
7. Missing B integration or report produces NOT_COMPARABLE, not an improvement claim.

## Metric definitions

- Detection/block rate = attack cases blocked before reaching the vulnerable application / attack cases executed.
- Miss rate = attack cases that reach and trigger vulnerable behavior / attack cases executed.
- False-positive rate = benign requests blocked / benign requests executed.
- Incremental benefit = B block rate minus A block rate on the same corpus.
- Added latency = B latency minus A latency for matching requests.
- Quorum propagation time = first valid alert submission to enforcement by the receiving policy.

A block response alone is insufficient: correlate edge logs with application-side request IDs to prove whether the request reached the app.

## Current status

- Stage 0 exists in repository CI.
- The three-node alert acceptance test uses loopback TLS and synthetic identities.
- The Shield Support Certificate is a signed evidence bundle, not an X.509 browser certificate.
- No actual OWASP CRS/WAF enforcement adapter connected to the Shield alert network is proven by Stage 0.
- Therefore the comparative result is **NOT RUN / NOT COMPARABLE**. Do not claim Node Core OS outperforms conventional controls until Stages 1–5 run with B genuinely integrated.