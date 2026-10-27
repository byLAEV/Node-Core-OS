# Portable Attestations — Product Specification

**Status:** Design proposal.

## Intended service

Represent signed, contextual claims about a specific event, action, qualification, or completed service. An attestation should identify its issuer, subject or pseudonymous reference, purpose, evidence references, issue time, validity or expiry where applicable, and correction/revocation mechanism.

## Principles

- Attestations are claims with provenance, not universal truth.
- Reputation should remain contextual and explainable rather than being reduced to a universal score.
- Users should be able to export and present attestations with consent, subject to clearly documented limitations.
- Corrections and disputes should be representable without pretending that historical events never occurred.
- Selective disclosure and privacy enhancements should be designed against explicit requirements; a hash of a proof is not the proof itself.

## Acceptance tests

Test signature validation, issuer identity, subject binding, scope/purpose mismatch, expiry, revocation or correction, evidence-reference integrity, and minimization of disclosed data.
