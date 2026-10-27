# Node Core OS Shield — Web Attack Lab

## Purpose

This prototype tests whether a loopback HTTPS service can combine the existing
Node Core OS Ed25519 node identity/TLS transport with signed security reports
and local request-rate limits.

## Implemented in this lab

- A synthetic HTTPS service bound only to `127.0.0.1`.
- Temporary Ed25519 identities and pinned self-signed Node Core OS certificates.
- Three synthetic reporter identities sign the same short-lived security observation.
- The service verifies reports using the existing `should_quarantine` primitive and
  blocks a node only when three distinct trusted reporter identities provide valid,
  unexpired signatures for that node.
- Altered signatures/records do not count toward the threshold.
- A local per-node request limit returns HTTP 429 after five accepted requests.

## Reproducible test

Run as an ordinary user from the repository root:

```bash
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
