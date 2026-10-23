# Network Test Evidence and GitHub Actions Plan

## Evidence record

Each domain test should produce a machine-readable JSON record with:

- schema/version
- domain name
- workflow run ID and commit SHA
- test start/end timestamps in UTC
- effective UID (must not be zero)
- test status: `PASS`, `FAIL`, `SKIPPED`, or `INCOMPLETE`
- checks performed and individual outcomes
- node identifiers as appropriate
- challenge/request ID and content digest where applicable
- evidence artifact paths and diagnostic summaries

Do not put secrets or private keys into artifacts.

## Workflow layers

### Pull request / push CI

- Validate workflow YAML syntax.
- Compile Python sources without writing bytecode into tracked locations.
- Run unit tests for network menu routing, native P2P, and Kubo adapters.
- Run local loopback transport tests under the ordinary runner user.
- Run isolated three-node propagation tests with independent data directories.
- Validate artifact schemas and assert that skipped tests are never mapped to PASS.
- Upload logs and JSON evidence even when a test fails, while excluding secrets.

### Manual live tests

Keep hardware/device-dependent Termux tests behind workflow_dispatch. Require explicit expected node identity and run-specific challenge. A manual test not invoked by a PR must remain SKIPPED and must not block unrelated unit tests, but must be listed as not verified for release readiness.

### Cross-VM and Kubo E2E

Run independent Ubuntu nodes for P2P/mesh and separate Kubo daemons for IPFS. Do not treat a Kubo-only test as coverage for native P2P. Pin tool versions where practical and retain failure diagnostics.

## Root prohibition

Every relevant job should explicitly assert effective UID != 0 before tests. Do not call sudo or su. GitHub-hosted Ubuntu runners normally use an unprivileged runner account; assert the fact instead of assuming it.

## Acceptance gates

- Syntax/unit: required on every PR.
- Local P2P: required when network transport code changes.
- Mesh: required when propagation/state code changes.
- Kubo: required when Kubo/CID/receipt code changes.
- Live Termux: report separately and require explicit PASS before claiming live-device verification.
- Any required test skipped unexpectedly is a workflow failure or INCOMPLETE result, not a PASS.
