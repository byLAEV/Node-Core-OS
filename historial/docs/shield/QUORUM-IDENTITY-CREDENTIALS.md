# Shield Quorum Identity Credentials — Prototype Contract

## Purpose

This module adds a cryptographically verifiable identity credential for a web application, service, server, database, host, or device. The credential binds an Ed25519 public key to a subject type, explicit scopes, a validity interval, and signatures from a configured quorum of Node Core OS identity nodes.

## Issuance and verification

1. Provision issuer identities through an explicit administrative enrollment process.
2. Configure each verifier with a trusted mapping of issuer node IDs to public keys. Do not trust keys merely because they appear inside a credential.
3. Create a credential with `create_quorum_identity_credential` using issuer stores and a threshold of at least two.
4. Deliver the credential to the target deployment through a controlled provisioning channel.
5. The service verifies it with `verify_quorum_identity_credential`, specifying its local issuer threshold, expected subject ID, and required scope.
6. Reject invalid, expired, tampered, insufficiently signed, or out-of-scope credentials.

The verifier-owned trust store and minimum threshold are authoritative; a credential cannot lower local policy. Duplicate signatures from one issuer do not count multiple times. Credential lifetime is capped at 90 days by this prototype.

## Security boundaries

- The credential is a signed JSON identity artifact, **not** an X.509 certificate trusted automatically by web browsers.
- Public website HTTPS still needs a valid certificate and correct TLS configuration for browsers.
- Signatures prove that trusted issuer keys signed the credential; they do not prove the issuers are independent operators or that the subject is benign.
- This module does not yet distribute issuance requests or signatures through the live P2P network. The caller supplies issuer stores. A later integration must gather approvals through authenticated Node Core OS transport and validate membership/threshold against a governance policy.
- This module does not yet install a WAF, alter firewall rules, protect a database, or stop DDoS. A credential only supplies identity and scoped authorization data; enforcement belongs to a separately tested Shield agent/proxy adapter.

## Tests

Run as a regular user from the repository root:

```bash
python -m unittest discover -s tests -p 'test_shield_identity_credential.py' -v
```

The tests use temporary identities and check quorum, tampering, expiry, trust-anchor enforcement, duplicate issuer rejection, and scope authorization. They are local unit tests and do not prove live P2P propagation or production protection.
