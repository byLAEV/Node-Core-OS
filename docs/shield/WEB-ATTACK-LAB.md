# Node Core OS Shield — Web Attack Lab

## Purpose

This prototype tests whether a loopback HTTPS service can combine the existing
Node Core OS Ed25519 node identity/TLS transport with signed security reports
and local request-rate limits.

## Implemented in this lab

- A synthetic HTTPS service bound only to `127.0.0.1`.
- Temporary Ed25519 identities and pinned self-signed Node Core OS certificates.
- Three synthetic reporter identities sign the same short-lived security observation.
- The service creates and verifies a short-lived Shield Support Certificate evidence
  bundle from the existing signed-event primitives. It blocks a node only when three
  distinct trusted reporter identities provide valid, unexpired signatures for that node.
- Each receiving node applies its own trusted-reporter list and minimum quorum policy;
  the support certificate cannot lower that local threshold.
- Altered signatures/records do not count toward the threshold.
- A local per-node request limit returns HTTP 429 after five accepted requests.

## Certificate model

The proposed CMI/SCC code was not copied into the lab because its optional trust anchor
would accept arbitrary self-signed roots when unset, and its sample server used plain
HTTP despite the port number. The useful idea retained is that a service/device identity
can be presented separately from a signed observation. This lab currently binds alerts
to existing Node Core OS node identities and TLS peer identity; it does **not** yet
implement CMI/SCC issuance, role authorization, or a production certificate hierarchy.

The Shield Support Certificate is an evidence bundle, not an X.509 certificate. Its
security comes from the reporter signatures inside it and the receiver's local trust
policy. It is a local, quorum-backed mitigation decision; no alert propagation between
real peers is implemented by this change.

## Reproducible test

Run as an ordinary user from the repository root:

```bash
python -m unittest discover -s tests -p 'test_shield_support.py' -v
python -m unittest discover -s tests -p 'test_shield_web_attack_lab.py' -v
```

GitHub Actions runs this test alongside the existing certificate, TLS, API abuse,
and distributed-defense unit tests.

## Important limits

This is an integration simulation, **not a live distributed-network attack test**.
The three reports are created by separate temporary keys and delivered to the
service in the test process. GitHub Actions does not thereby prove that real
Node Core OS peers propagated those messages, that the keys belong to independent
operators, or that revocation converges across network partitions.

The test covers application-layer behavior after a TLS connection is established.
It does not simulate volumetric DDoS, saturated network links, browser trust stores,
a production reverse proxy, or a production website. A certificate identifies a
key; it does not itself stop traffic. Local limits continue to apply independently
of remote reports.

## Status

Prototype code and deterministic loopback tests are added on the feature branch.
Do not label this production-ready until the test suite passes in Actions, a real
transport path for signed alerts is integrated and tested across independent
nodes, replay/anti-rollback and Sybil/collusion defenses are assessed, and load
tests plus an independent security review are completed.
