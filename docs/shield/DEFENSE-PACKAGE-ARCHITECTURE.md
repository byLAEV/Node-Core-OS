# Node Core OS Shield — Defense Package Architecture

**Status:** architecture and implementation contract; not a production-ready universal installer.

## Objective

Provide a reusable defense package for websites, web applications, server infrastructure, databases, and supported endpoint devices. The package combines established local security controls with Node Core OS identities and signed, short-lived threat evidence exchanged between trusted nodes.

The design MUST NOT claim that certificates alone prevent attacks or that one installation protects every protocol and device class. Each deployment profile must declare its supported traffic, platform, controls, and limitations.

## Security model: five distinct artifacts

1. **Public-facing TLS certificate:** standard browser/server PKI certificate used to authenticate HTTPS to ordinary browsers and clients. Node Core OS identity keys do not automatically replace public Web PKI.
2. **Node identity credential:** identifies a Node Core OS peer for authenticated node-to-node communication. Trust is established by local policy, not by a self-asserted identifier alone.
3. **Service/device identity credential:** binds a service or device key to a defined identity and lifecycle. Authorization must be checked separately.
4. **Shield Support Certificate:** a versioned, short-lived evidence bundle containing independently signed security observations. It is not an X.509 certificate and does not itself authorize a global ban.
5. **Signed policy bundle:** defines allowed actions, scope, expiry, thresholds, and revocation version. A receiver MUST reject an unsigned, expired, stale, malformed, or policy-incompatible bundle.

Do not conflate key ownership with human uniqueness, professional qualifications, innocence, or truth of a report.

## Defense layers

### Layer A — Edge and volumetric protection

Use an upstream DDoS mitigation service, CDN, or network provider where required. A local certificate, reverse proxy, or application firewall cannot protect a saturated upstream network link.

### Layer B — HTTP(S) reverse proxy and WAF

Place a maintained reverse proxy and Web Application Firewall (for example, Nginx with OWASP ModSecurity Core Rule Set) in front of the application. Start with detection/logging in a controlled environment, tune false positives, and enable blocking only after validation. Use TLS correctly, request/body size limits, timeouts, connection limits, and rate limits.

Do not implement a new WAF rule engine from scratch when a maintained engine is available. The Node Core OS package should integrate with it through documented configuration and adapters.

### Layer C — Node Core OS local Shield agent

The local agent should run with least privilege and provide:
- verified local policy and trust-store management;
- signed audit events with bounded retention;
- a local control interface restricted to loopback or authenticated IPC;
- replay protection, expiry, revocation and policy-version checks;
- fail-safe behavior: loss of the peer network must not disable local WAF/TLS/rate limits;
- dry-run mode, explainable decisions, and explicit rollback.

The agent must not have unrestricted access to application secrets or database contents.

### Layer D — Distributed threat evidence

Peers exchange signed observations through the existing authenticated Node Core OS transport. Every receiving node independently verifies signatures, reporter trust, event age, replay state, subject, scope, revocation state, and its own quorum policy.

A quorum is not proof of independent operators: Sybil identities and collusion must be addressed separately. Remote reports should initially create a risk signal or temporary scoped mitigation, not an irreversible global ban. Provide expiry, reason codes, auditability, and manual override.

### Layer E — Database and endpoint profiles

- **Database:** never expose the database port publicly by default; use network segmentation, least-privilege credentials, TLS, parameterized queries, connection limits, patching, backup/restore tests, and audit logs. The Shield may consume security events and enforce network policy, but it cannot replace database authorization or application query safety.
- **Servers:** integrate with host firewall, service manager, log source, and reverse proxy through explicit adapters.
- **Endpoints/IoT:** separate profiles by operating system, privileges, update mechanism, and available telemetry. Do not promise a single portable agent for every device.
- **Web applications:** protect at the edge and application layer; retain application authentication, authorization, CSRF protections, secure sessions, input validation, and dependency patching.

## Deployment profiles

1. web-edge: reverse proxy + maintained WAF + TLS + bounded rate limits + local audit.
2. node-peer: node identity + authenticated transport + signed threat-event verification.
3. database-segment: private network exposure + least-privilege access + TLS + audit integration.
4. host-agent: host-specific telemetry and firewall integration, installed only on supported Linux distributions initially.
5. endpoint-agent: future, platform-specific profiles after threat-model and compatibility testing.

Every profile must document installation, configuration, upgrades, uninstall/rollback, privileges, network ports, data collected, log retention, and how to disable remote mitigations safely.

## Threats and required controls

| Threat | Required control | Must not claim |
|---|---|---|
| TLS interception / impostor service | Valid TLS, hostname verification, correct trust anchors, peer identity binding | That a signature encrypts traffic |
| SQL injection / XSS / common HTTP attacks | Maintained WAF rules plus application fixes and security tests | That certificates sanitize input |
| Credential stuffing / request floods | Authentication controls, rate/concurrency limits, upstream capacity where needed | That a local limiter stops volumetric DDoS |
| Forged security reports | Signature verification and receiver-owned trust policy | That any signed report is truthful |
| Replay / stale revocation | Nonces or event IDs, bounded replay cache, monotonic policy/revocation versions, expiry | That timestamps alone prevent all replay |
| Sybil / colluding reporters | Enrollment policy, operator diversity where available, reputation and rate limits, conservative action | That three keys necessarily mean three independent actors |
| Network partition | Local enforcement, expiry, queued signed events, explicit stale-state policy | Instant global consensus |
| Compromised Shield agent | Least privilege, signed updates, narrow IPC, audit, recovery procedure | That peer consensus repairs a compromised host automatically |

## Rollout plan and acceptance gates

### Gate 0 — Repository audit
Confirm the exact code on main, workflow status, supported Python/platform versions, and boundaries between test-only code and runtime services.

### Gate 1 — Local web-edge package
Deliver a reproducible deployment profile based on maintained reverse proxy/WAF components, with a harmless sample app and a local test CA. Test legitimate traffic, common attack payloads, malformed/oversized bodies, request-rate limits, TLS failures, logging, and false positives. No external target is used.

### Gate 2 — Identity adapter
Bind service/node identities to the local agent and authenticate peer traffic. Require explicit trust anchors and fail closed when mandatory trust configuration is absent.

### Gate 3 — Distributed event path
Send signed security observations between independent processes over the actual authenticated Node Core OS transport. Test forged reports, replay, expiry, revocation, partitions, reconnection, duplicates, and malformed messages.

### Gate 4 — Policy enforcement
Convert accepted evidence into temporary, scoped, reversible mitigations. A remote event must not directly edit firewall rules or block identities without local policy approval.

### Gate 5 — Platform profiles
Add database, host, and endpoint adapters one at a time, with separate integration tests and installation/rollback documentation.

### Gate 6 — Load and independent review
Run controlled load tests, measure latency and resource usage, record false-positive/negative rates, review the threat model, and arrange an independent security review before making production-readiness claims.

## Required CI evidence

GitHub Actions must publish the tested commit, exact commands, test counts, failures, and artifacts/logs. A test is considered passed only if it actually executed and its assertions succeeded. Unit tests and loopback simulations must be labelled as such; they do not prove live distributed propagation or production resilience.

## Current implementation boundary

The existing Shield web attack lab and node_core/security/shield_support.py provide a local prototype for signed evidence, quorum checks, temporary validity, and synthetic loopback behavior. They do not yet provide a production WAF, universal device installer, or live propagation of Shield alerts across independent peers. This document defines the intended integration path without overstating current functionality.
