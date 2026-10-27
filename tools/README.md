# Identity Tools and Services byLAEV

**Location:** Node Core OS byLAEV  
**Status:** Product catalog and design specifications — not a production service declaration.

This directory is reserved for the identity-related tools and service products that personal identities and their authorized nodes may use to create verifiable value within Node Core OS. It is intentionally separate from the core runtime: product definitions and acceptance criteria live here; reusable runtime capabilities belong in the appropriate `node_core/` modules after their contracts and tests are established.

## Purpose

The goal is to turn identity and node participation into useful, auditable services. Potential capabilities include credential lifecycle management, device identity, verification of signed claims, access and abuse controls, portable attestations, evidence of completed tasks, and eventually a service marketplace.

The intended business model is to pay for **real, requested, measurable and accepted services**. Identity itself is not the product to be sold, and income is not guaranteed by registration, node ownership, uptime, recruitment, or token holding.

## Maintained product and service catalog

The complete, versioned catalog for potentially monetizable node work lives in [`tools/catalog/`](catalog/README.md). It separates service definitions and acceptance evidence from economic policy. The distribution of benefits, prices, fees, and reward formulas remain `pending-consensus` until approved through the project's business-model consensus process. No payment implementation or income guarantee is implied.

See the [catalog index](catalog/README.md), [economic consensus record](catalog/ECONOMIC-CONSENSUS.md), [service template](catalog/SERVICE-TEMPLATE.md), and [service-family index](catalog/services/README.md).

## Product catalog

| Product family | Intended capability | Status in this catalog |
| --- | --- | --- |
| **CMI — Certificado Maestro de Identidad** | Proposed identity-root credential and issuer/evidence references. | Design proposal |
| **SCC — Subcertificado de Dispositivo** | Proposed subordinate credential for a device or node, with scoped permissions and lifecycle. | Design proposal |
| **Credential Verification** | Validate signatures, issuer trust, validity period, profile and revocation status. | Requirements to define and implement |
| **Node Security Services** | Authorization, rate limits, anomaly handling, signed audit events and service health. | Requirements to define and implement |
| **Portable Attestations** | Exchangeable, signed, purpose-scoped claims with evidence and correction/dispute paths. | Design proposal |
| **Operator Services** | Work allocation, task evidence, acceptance and transparent compensation rules. | Future product layer |
| **Service Marketplace** | Customer billing, operator settlement, fees, disputes and reporting. | Future product layer |

These entries define intended products, not proof that their implementations exist or are production-ready.

## Architectural boundaries

- **Person identity is not node identity.** A node key proves control of that key; it does not independently prove a person's civil identity or uniqueness.
- **Credential integrity is not claim truth.** A valid signature establishes that a particular key signed particular data; issuer authority and supporting evidence must be checked separately.
- **Authentication is not authorization.** Every action requires a scoped permission and policy check.
- **Node count is not human vote count.** Multiple nodes belonging to one person must not automatically multiply that person's participation in human governance.
- **Reputation is evidence, not a universal score.** Attestations need context, provenance, correction and dispute mechanisms.
- **Payment follows accepted work.** Define task, customer, evidence, acceptance, price, fees, settlement, and disputes before distributing funds.
- **Privacy is explicit.** Do not publish personal data by default. Define consent, retention, deletion, recovery, and disclosure boundaries.
- **No unsupported security claims.** CMI/SCC certificates alone do not prevent Sybil attacks, denial of service, key theft, or impersonation.

## Proposed directory map

```text
tools/
├── README.md
├── cmi-scc/
│   └── SPECIFICATION.md
├── credential-verification/
│   └── SPECIFICATION.md
├── node-security/
│   └── SPECIFICATION.md
├── attestations/
│   └── SPECIFICATION.md
└── operator-services/
    └── SPECIFICATION.md
```

These are product/specification boundaries. They do not replace existing identity modules or imply that code should be copied into this directory. When a tool is implemented, its runtime module should live where the existing architecture calls for it; this directory should retain its product contract, user-facing scope, and acceptance criteria.

## Minimum staged acceptance criteria

### Stage 0 — Product definition
- Define users, customers, roles, data handled, threat model, failure cases, and exclusions.
- Define status vocabulary: proposed, implemented, tested, security-reviewed, and production-operated.
- Define how to demonstrate each claim with reproducible evidence.

### Stage 1 — Credential primitives
- Specify deterministic serialization and exact bytes covered by signatures.
- Use real cryptographic libraries and strict key/signature encoding validation.
- Specify issuer trust, subject binding, validity, expiry, revocation and key rotation.
- Add positive, negative, malformed-input, tampering, expiry and revocation tests.
- Do not represent a hash of a proof as the proof itself.

### Stage 2 — Node authorization and evidence
- Bind credentials to explicit scopes and authorization policies.
- Add replay-resistant challenges where proof of current key control is required.
- Implement server-side rate limits and abuse handling independently of certificate validity.
- Produce verifiable service-task evidence without exposing unnecessary personal data.

### Stage 3 — Operator services
- Define each task, eligibility, quality requirements, completion evidence and acceptance process.
- Establish customer-funded revenue before promising participant rewards.
- Document fees, payout timing, disputes, fraud controls, tax and legal responsibilities.
- Never guarantee income or pay solely for recruiting participants.

### Stage 4 — Privacy and scale
- Review selective disclosure, data minimization, recovery and privacy-preserving proofs against explicit requirements.
- Add independent security review and deployment monitoring before production claims.

## Relationship to Node Core OS

Node Core OS supplies shared infrastructure. Tools define bounded capabilities and products. Protocols define rules for coordination. Applications use those capabilities for specific purposes. The business layer must not silently become a core identity authority, override a user's consent, or grant privileges merely because a credential exists.

See the main [Node Core OS README](../README.md), [Identity Design Principles](../docs/IDENTITY-DESIGN-PRINCIPLES.md), and [Architecture](../docs/ARCHITECTURE.md).
