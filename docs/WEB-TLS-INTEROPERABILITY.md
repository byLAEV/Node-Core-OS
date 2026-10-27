# Node Core OS Web TLS Interoperability Profile

## Purpose

This profile lets a Node Core OS identity sign a portable binding between its Ed25519 node identity and an already-issued HTTPS X.509 certificate for a DNS name. It is separate from the self-signed certificate used by the private Node Core OS P2P transport.

## Two independent trust checks

1. **Web PKI / HTTPS:** browsers, smart TVs, consoles, and operating systems validate the server certificate chain against their own trusted root store, check the requested hostname against Subject Alternative Name (SAN), enforce validity dates, and apply platform policy. This project does not override or replace those checks.
2. **Node Core OS binding:** the node identity signs a canonical JSON record containing the node ID, raw Ed25519 public key, exact DNS name, SHA-256 fingerprint of the exact PEM certificate bytes, and certificate validity interval. A verifier can check that signature and binding independently.

A valid Node Core OS binding does not make a certificate trusted by a browser. A valid public HTTPS certificate does not, by itself, prove that the service is operated by a particular Node Core OS node.

## Certificate requirements

- A certificate already issued by a public Web PKI CA trusted by the target device, or by an explicitly configured private CA on a managed network.
- Exact DNS name in the X.509 Subject Alternative Name extension.
- Extended Key Usage containing TLS Web Server Authentication (serverAuth).
- Certificate is within its validity interval.
- If Key Usage is present, digitalSignature must be permitted.
- No wildcard DNS names in Node Core OS bindings; create a separate exact-name binding for each DNS name.

The module does not create a public certificate, perform ACME issuance, or validate the complete CA chain. Use a standard TLS server (for example, a correctly configured web server) and its supported certificate automation. Do not install a private CA on unmanaged devices or attempt to bypass their trust controls.

## API

- `create_web_certificate_binding(identity_store, certificate_pem, dns_name)` returns a signed JSON-compatible dictionary.
- `verify_web_certificate_binding(binding, certificate_pem, expected_dns_name)` verifies the Node Core OS signature and certificate binding.

Keep the private Node Core OS identity key on the node. Publish only the public binding and certificate. Renewing or replacing the HTTPS certificate changes its fingerprint; issue and distribute a new binding after renewal.

## Scope and limitations

This is an identity-binding profile, not a universal anti-hacking certificate. It does not prevent application vulnerabilities, phishing on lookalike domains, DNS compromise, denial-of-service, compromised devices, or malicious code. Browser/platform HTTPS validation and application security remain necessary. Consumer devices differ: some accept ordinary publicly trusted HTTPS without configuration, while others do not allow user-installed roots or custom application certificates.

## Status

Experimental profile. The included tests use synthetic local certificates. It is not a production certification and does not claim universal TV/console compatibility.
