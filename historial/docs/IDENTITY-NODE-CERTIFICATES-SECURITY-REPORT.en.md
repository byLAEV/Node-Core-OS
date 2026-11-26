# Official Technical Report: Node Identity and Certificate Security in Node Core OS byLAEV

**Author and design lead:** Lerry Alexander Elizondo Villalobos — **byLAEV**  
**Project:** Node Core OS byLAEV  
**Review date:** October 27, 2026  
**Document status:** Technical report based on the repository code and linked CI runs. It is not an independent certification or a guarantee of production security.  
**Repository:** https://github.com/byLAEV/Node-Core-OS  
**Reference implementation merge:** [73c2d2237139b7c373d5fea230d3787a541833ff](https://github.com/byLAEV/Node-Core-OS/commit/73c2d2237139b7c373d5fea230d3787a541833ff)

---

## 1. Executive summary

Node Core OS includes a persistent technical identity for nodes based on Ed25519 keys, together with a TLS transport layer that associates a node certificate with the public key of that identity. The security work introduced in PR #150 adds synthetic adversarial tests, a laboratory HTTPS service, validation of a web certificate profile, HTTPS validation using standard chain and hostname checks, local primitives for signed security events and revocation, local corroboration rules, and limited API-abuse tests.

The certificate GitHub Actions suite completed successfully on commit `024c563bedf3cffda2af391931d4ebcafc1dbd62`. PR #150 was merged into `main` using the implementation merge commit referenced above. CI demonstrates that the automated cases for that version completed without test failures; it does not prove the absence of vulnerabilities, resistance to every attack, or the existence of a complete distributed defense system.

**Main conclusion:** the technical contribution is to add verifiable node identity and testable security components alongside TLS. It does not replace HTTPS/X.509 and does not, by itself, guarantee protection against phishing, DDoS, malware, or application vulnerabilities.

## 2. Purpose and scope

The system targets GNU/Linux terminals running as a normal user. The Termux-specific workflow `termux-live-peer.yml` was removed from the certificate PR because it did not match the intended platform scope for these tests.

This report covers:

- Cryptographic node identity and certificate binding.
- Rejection tests for tampered certificates or metadata.
- A local HTTPS laboratory using synthetic identities.
- Binding between a web certificate and a node identity.
- HTTPS validation using a trusted chain and hostname checks.
- Signed security events, local revocation snapshots, and corroboration.
- Bounded API-abuse tests.
- Limitations, outstanding threats, and reproduction instructions.

This report does not provide an independent audit of the entire repository, penetration testing against public services, formal PKI certification, an academic cryptographic analysis, or proof of defense on televisions, consoles, or other commercial devices.

## 3. Concepts and trust model

### 3.1 Node identity

The technical implementation uses Ed25519 and derives a node identifier prefixed with `sha256:` from the public key. The private key can sign messages and demonstrate control of that key. The public key and identifier allow a verifier to check whether a signature corresponds to the declared technical identity.

This does not, by itself, prove:

- a person's civil identity;
- that a person is unique;
- that an operator is honest or trustworthy;
- that a device is uncompromised;
- that signed content is true;
- that a node is authorized to perform any arbitrary action.

References:
- [Node identity implementation](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/identity/node_identity.py)
- [Identity association tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_identity_associations.py)
- [Identity functionality tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_identity_function.py)

### 3.2 Node TLS transport certificate

The TLS transport associates the certificate presented by a node with the public-key identity stored by that node. Tests check rejection of cases including a certificate associated with a different node, malformed PEM, tampered metadata, a modified signature, an expired certificate, and an invalid self-signature.

Node Core OS-specific validation must not be confused with a complete public-key infrastructure (PKI). The transport laboratory uses explicit trust in synthetic certificates and node-identity binding. This is useful for testing trust between known nodes, but it does not replace the standard web-certificate validation performed by a browser.

Reference:
- [Node TLS transport](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/p2p/tls_transport.py)

### 3.3 Standard HTTPS

HTTPS/X.509 provides server authentication and an encrypted channel when the client correctly validates the certificate chain, validity period, and requested hostname. Node Core OS must preserve these guarantees when interacting with conventional websites.

The standard HTTPS test uses a test-generated CA and synthetic certificates and connects only to loopback. It checks acceptance of a valid case and rejection of negative cases, including a wrong hostname, an untrusted CA, and a certificate that is not yet valid. This is a local integration test, not a test against a public website.

Reference:
- [HTTPS standard-validation tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_standard_https_validation.py)

### 3.4 Web certificate binding profile

The web profile can create and verify a signed association between a certificate, a DNS name, and a node identity. Tests include valid binding, a modified binding signature, a different certificate fingerprint, incorrect DNS, an expired certificate, a missing server-auth EKU, and a missing SAN.

Binding to a node identity is an additional technical attribution signal. It does not automatically make a certificate publicly trusted and must not be used to bypass a client's normal chain, hostname, or trust-policy checks.

References:
- [Web TLS profile implementation](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/identity/web_tls_profile.py)
- [Web TLS profile tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_web_tls_profile.py)

## 4. Security components covered by tests

### 4.1 Certificate adversarial tests

Cases cover a valid node-key binding, a certificate associated with another node, malformed PEM, modified metadata, a modified signature, an expired certificate, and an invalid self-signed certificate.

- [Test source](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_certificate_security.py)
- [GitHub Actions run](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438209)

### 4.2 Protected HTTPS web laboratory

The laboratory starts an HTTPS service on `127.0.0.1` using temporary certificates. It checks access by a trusted node client, rejection of an untrusted client certificate, and rejection of an impostor server whose certificate does not match the certificate expected by the client.

The test explicitly evaluates transport using explicitly trusted certificates and node-identity binding; it is not a browser PKI test.

- [Web laboratory tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_certificate_web_lab.py)

### 4.3 Signed events, revocation snapshots, and corroboration

The distributed-defense module provides primitives to:

- create and verify signed security events;
- validate authorized issuers, signatures, timestamps, and evidence fingerprints;
- create and verify signed revocation snapshots with sequence numbers;
- reject unauthorized or expired snapshots and snapshots whose sequence is not greater than the last known sequence;
- locally decide whether enough distinct reporters with valid signed events meet a corroboration threshold.

References:
- [Distributed defense and signed-event implementation](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/security/distributed_defense.py)
- [Distributed-defense tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_distributed_defense.py)

**Critical limitation:** these primitives and tests do not, by themselves, demonstrate effective distribution of revocations between nodes, anti-rollback persistence after a restart, convergence during network partitions, or automatic quarantine execution. The corroboration function evaluates local evidence; it does not prove that reporters are independent people or independently controlled organizations. Multiple keys can be controlled by one entity.

### 4.4 Bounded API-abuse tests

The suite includes malformed input, oversized requests, and rate-limit scenarios in a synthetic loopback handler. This tests that laboratory handler's behavior; it does not prove that every real Node Core OS endpoint is protected.

- [API-abuse laboratory tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_api_abuse_lab.py)

### 4.5 P2P TLS transport

- [P2P TLS transport tests](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_p2p_tls_transport.py)

## 5. Reproducible CI evidence

The GitHub Actions workflow defines the laboratory commands and scope:

- [Certificate adversarial-test workflow](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/certificate-adversarial-tests.yml)
- [Primary certificate run: #40450438209](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438209)
- [Additional certificate run: #40450434087](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450434087)
- [GNU/Linux CI: #40450438106](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438106)
- [User-only Kubo integration: #40450438099](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438099)
- [Three Ubuntu nodes and P2P contracts: #40450438116](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438116)
- [Three-node E2E tests: #40450438162](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438162)
- [Installer E2E tests: #40450438183](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438183)
- [Independent network domains: #40450438270](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438270)
- [Merged PR #150](https://github.com/byLAEV/Node-Core-OS/pull/150)
- [Implementation merge commit](https://github.com/byLAEV/Node-Core-OS/commit/73c2d2237139b7c373d5fea230d3787a541833ff)

The workflow runs the following suites using Python 3.12 and the repository dependencies, then compiles the modules to detect syntax errors:

```bash
python -m unittest discover -s tests -p 'test_certificate_security.py' -v
python -m unittest discover -s tests -p 'test_certificate_web_lab.py' -v
python -m unittest discover -s tests -p 'test_web_tls_profile.py' -v
python -m unittest discover -s tests -p 'test_standard_https_validation.py' -v
python -m unittest discover -s tests -p 'test_distributed_defense.py' -v
python -m unittest discover -s tests -p 'test_api_abuse_lab.py' -v
python -m unittest discover -s tests -p 'test_p2p_tls_transport.py' -v
python -m compileall -q node_core/security node_core/identity tests
```

### Reproducing on GNU/Linux as a normal user

From a clean repository checkout and inside a Python virtual environment, without running as root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m unittest discover -s tests -p 'test_certificate_security.py' -v
python -m unittest discover -s tests -p 'test_certificate_web_lab.py' -v
python -m unittest discover -s tests -p 'test_web_tls_profile.py' -v
python -m unittest discover -s tests -p 'test_standard_https_validation.py' -v
python -m unittest discover -s tests -p 'test_distributed_defense.py' -v
python -m unittest discover -s tests -p 'test_api_abuse_lab.py' -v
python -m unittest discover -s tests -p 'test_p2p_tls_transport.py' -v
python -m compileall -q node_core/security node_core/identity tests
```

The tests are designed to use synthetic identities and certificates, temporary directories, and local connections. They must not be interpreted as authorization to test third-party systems.

## 6. Technical comparison with conventional HTTPS/X.509 certificates

| Capability | Standard HTTPS/X.509 | Node Core OS within the tested scope |
|---|---|---|
| Validate certificate chain, dates, and hostname | Yes, when the client is correctly configured | Standard validation is tested in a local laboratory |
| Bind a certificate to a technical node identity | Not a universal feature of basic X.509 | Node-key/identity binding and a web profile are tested |
| Sign security events with node keys | Not a basic TLS-certificate function | Local signed-event primitives and tests exist |
| Distribute and apply revocations across nodes | Depends on the PKI and distribution system used | Local primitives are tested; full distributed propagation is not |
| Stop phishing, DDoS, malware, or application flaws | Not by itself | Not demonstrated by these certificates or tests |
| Prove that a key belongs to one unique person | No | A technical node identity does not prove this either |

Accordingly, this report does not claim that Node Core OS is cryptographically superior to X.509 or replaces web trust infrastructure. Its potential differentiator is the node-identity and signed-evidence layer that can complement conventional TLS and, after full integration, help coordinate trust decisions among nodes.

## 7. Outstanding threats and required work

Before claiming production readiness, at least the following work should be completed and documented:

1. **Distributed revocation:** authenticated snapshot transport, persistence of the accepted sequence, replay and rollback tests, disconnected-node behavior, and recovery after restart.
2. **Operational containment:** integrate local decisions with authorization policy, reversible quarantine, audit logging, and recovery procedures.
3. **Sybil resistance:** define how reporters are authorized and how multiple keys under common control are prevented from counting as genuinely independent corroboration.
4. **Real API abuse testing:** test integrated endpoints in an isolated environment, measure load, rate limits, latency, and availability, and document out-of-scope components.
5. **PKI lifecycle:** document issuance, renewal, key custody, expiry, revocation, recovery, and response to key compromise.
6. **Independent review:** obtain an independent review of the threat model, cryptographic code, secret handling, TLS configuration, and dependencies.
7. **Comparative testing:** compare standard HTTPS with HTTPS plus the Node Core OS layer under equivalent conditions, using metrics such as false positives, false negatives, revocation latency, and availability.

## 8. Security and use statement

This report documents the referenced code and test status; it is not an absolute security guarantee. A valid certificate supports only the claims that its format, issuer, trust chain, and validation policy allow a verifier to establish. A signature demonstrates control of the corresponding key and integrity of the signed message; it does not guarantee the truth of the message's contents.

Protecting a service also requires correct authentication and authorization, TLS configuration, updates, access controls, resource limits, observability, abuse mitigation, backups, and incident response. No standalone certificate eliminates every attack vector.

Do not install these certificates as a global trust authority or deploy them to production services, televisions, or consoles without a platform-specific interoperability profile, issuance and revocation processes, and a dedicated security assessment.

## 9. Authorship

**Lerry Alexander Elizondo Villalobos — byLAEV**  
Author and design lead of Node Core OS byLAEV.

This document attributes authorship of the design and project responsibility to byLAEV. CI results are automated repository results, not an independent external certification.

---

**Primary references**
- [Node Core OS byLAEV repository](https://github.com/byLAEV/Node-Core-OS)
- [PR #150 — certificate adversarial tests](https://github.com/byLAEV/Node-Core-OS/pull/150)
- [Certificate test workflow](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/certificate-adversarial-tests.yml)
- [Certificate test run #40450438209](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438209)
- [Implementation merge commit](https://github.com/byLAEV/Node-Core-OS/commit/73c2d2237139b7c373d5fea230d3787a541833ff)
