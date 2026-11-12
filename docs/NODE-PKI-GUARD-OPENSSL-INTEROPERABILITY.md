# NODE-PKI-GUARD X.509 / OpenSSL Interoperability Profile v1.0

**Status:** public interoperability specification for the constrained X.509 issuance and validation components. This document describes the file formats and verification procedure; it is not a claim of WebPKI, CA/B Forum, FIPS, or external audit certification.

## 1. Compatibility objective

NODE-PKI-GUARD certificates are ordinary X.509 certificates encoded as PEM or DER. OpenSSL users and applications that consume RFC 5280 certificates can parse and validate them using their normal X.509 tooling.

NODE-PKI-GUARD does not replace X.509, PEM, DER, PKCS#10, or OpenSSL. The NODE-specific authorization system is an additional administrative control plane. A relying party may validate a conventional X.509 certificate without implementing NODE identity, NODE-PKI-BINDING, or UTXO, provided its own trust and policy requirements are met.

## 2. Public artifact formats

| Artifact | Format | Purpose |
|---|---|---|
| End-entity certificate | X.509 DER; PEM armor for distribution | Standard certificate |
| CSR | PKCS#10 DER or PEM | Public-key and requested-subject submission |
| CA certificate(s) | X.509 PEM/DER | Trust anchor and intermediate chain |
| CRL, when issued | X.509 CRL PEM/DER | Revocation distribution |
| Package manifest | UTF-8 JSON | Package inventory and fingerprints |
| NODE-PKI-BINDING, optional | Versioned JSON | Links a NODE identity to an X.509 certificate |
| UTXO authorization/receipt, optional | Versioned NODE protocol data | Administrative authorization evidence |

The X.509 certificate remains independently usable. NODE-specific JSON sidecars are not X.509 extensions and are not required by generic OpenSSL clients.

## 3. Distribution layout

A public certificate bundle may use this layout:

```text
node-pki-guard-bundle/
├── manifest.json
├── certs/
│   ├── certificate.pem
│   ├── certificate.der
│   └── chain.pem
├── trust/
│   └── roots.pem
├── crl/
│   └── issuer.crl.pem
└── node/
    └── binding.json
```

Only include artifacts that actually exist. Do not distribute private keys, passwords, seed phrases, or UTXO signing secrets in a public bundle. The optional node/binding.json is omitted for generic X.509 deployments.

## 4. OpenSSL command-line verification

Commands below assume OpenSSL is installed and the relying party has independently obtained and trusted the correct root CA. Never trust a root certificate merely because it arrived in the same untrusted download as the leaf certificate.

Inspect certificate:

```sh
openssl x509 -in certs/certificate.pem -noout -subject -issuer -serial -dates
openssl x509 -in certs/certificate.pem -noout -fingerprint -sha256
openssl x509 -in certs/certificate.pem -pubkey -noout
```

Verify a TLS server certificate and DNS identity:

```sh
openssl verify -x509_strict -auth_level 2 \
  -purpose sslserver -verify_hostname service.example.com \
  -CAfile trust/roots.pem -untrusted certs/chain.pem \
  certs/certificate.pem
```

If there are no intermediate certificates, omit `-untrusted certs/chain.pem`. If the certificate is for a TLS client, use `-purpose sslclient` and the appropriate client identity policy. For an IP address, use `-verify_ip 192.0.2.10` instead of `-verify_hostname`.

Verify with a current CRL when the deployment requires revocation checking:

```sh
openssl verify -x509_strict -auth_level 2 \
  -purpose sslserver -verify_hostname service.example.com \
  -CAfile trust/roots.pem -untrusted certs/chain.pem \
  -CRLfile crl/issuer.crl.pem -crl_check_all \
  certs/certificate.pem
```

A successful path validation without a CRL does not establish that the certificate is not revoked. OpenSSL does not automatically fetch or refresh CRLs or perform OCSP in these commands.

For DER input, use `-inform DER` with `openssl x509` inspection commands. Convert formats without changing the certificate:

```sh
openssl x509 -inform DER -in certs/certificate.der -out certs/certificate.pem
openssl x509 -in certs/certificate.pem -outform DER -out certs/certificate.der
```

## 5. CSR generation and submission

Example CSR generation using OpenSSL and a locally protected private key:

```sh
openssl req -new -newkey ed25519 -keyout node-private-key.pem \
  -out node-request.csr.pem -subj "/CN=service.example.com" \
  -addext "subjectAltName=DNS:service.example.com"
chmod 600 node-private-key.pem
```

This command creates a private key and CSR locally. The private key MUST remain with its owner and MUST NOT be uploaded with the CSR. The current NODE-PKI-GUARD constrained issuer accepts PKCS#10 CSR input, checks proof of possession, and applies an issuer-controlled profile. It does not automatically authorize issuance through UTXO; the application service integration is a separate requirement.

## 6. Fingerprint and manifest rules

- Certificate fingerprint: lowercase hexadecimal SHA-256 over the DER-encoded certificate.
- SPKI fingerprint: lowercase hexadecimal SHA-256 over DER SubjectPublicKeyInfo.
- File hashes in manifest.json: lowercase hexadecimal SHA-256 over the exact file bytes.
- Paths: relative POSIX paths within the bundle; no absolute paths or parent-directory traversal.
- A manifest is an inventory, not a trust anchor or a signature. Authenticate the manifest through a trusted release signature, authenticated transport, or an independently published digest.

## 7. Optional NODE identity binding

For NODE Core OS deployments, NODE-PKI-BINDING links the identity to the X.509 certificate using the certificate and SPKI fingerprints and proof-of-possession evidence. Its schema is published at `schemas/node-pki-binding.schema.json`.

Generic OpenSSL users do not need to parse this binding. Conversely, possession of a valid X.509 certificate alone does not prove a NODE-PKI-BINDING is active or that a NODE UTXO authorization is valid.

## 8. Current implementation boundary

- The repository contains a constrained CSR-to-X.509 issuance primitive.
- The repository contains an OpenSSL-based X.509 path-validation adapter with explicit trust bundle and peer-identity checking.
- The X.509 output is standard certificate data, not a proprietary certificate encoding.
- The full lifecycle service that atomically authorizes UTXO use, persists certificates, performs durable idempotency/recovery, and issues administrative receipts is not yet complete.
- No production Network ledger, distributed finality, automatic CRL distribution, or OCSP client is claimed by this profile.

## 9. Compatibility test

At minimum, an interoperability test must:

1. Generate a CSR using OpenSSL.
2. Issue a leaf certificate using a test CA and an approved issuance profile.
3. Inspect the resulting PEM with `openssl x509`.
4. Verify chain, purpose, and expected hostname with `openssl verify`.
5. Convert PEM to DER and back, then compare certificate fingerprints.
6. Demonstrate rejection for an untrusted CA, wrong hostname, expired certificate, and (when enabled) revoked certificate.

Run repository tests from the project root:

```sh
python -m unittest tests.test_node_pki_guard_issuer tests.test_node_pki_guard_x509 -v
```

Passing repository tests does not replace interoperability testing against the OpenSSL versions and deployment policies used by a relying party.
