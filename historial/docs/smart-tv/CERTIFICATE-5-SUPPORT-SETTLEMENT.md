# Smart TV Credential 5 — Support Authorization and Settlement

**Status:** commercial/technical contract proposal. It does not implement Lightning Network, Liquid, a wallet, a payment rail, or an executable contract.

## Purpose

Authorize a specific support task and make payment eligibility depend on accepted, evidenced work—not merely on a security alert, node participation, certificate issuance, or the number of nodes involved.

## Required work order

A signed work order should contain:
- unique work-order ID and expiry;
- customer/device reference with minimal personal data;
- exact authorized scope and exclusions;
- service provider identity/key and conflict-of-interest declarations;
- task description, expected deliverables, acceptance tests and evidence format;
- maximum price, currency/asset, fees and refund/dispute rules;
- explicit customer consent and authorization to touch the device;
- whether the task can change firmware, configuration, credentials, or privacy controls;
- rollback and recovery requirements;
- settlement condition and authorized approver.

## Lifecycle

```text
ALERT -> TRIAGE -> PROPOSED_WORK_ORDER -> CUSTOMER_APPROVAL
      -> PROVIDER_ACCEPTANCE -> AUTHORIZED_EXECUTION
      -> EVIDENCE_SUBMISSION -> INDEPENDENT_OR_CUSTOMER_ACCEPTANCE
      -> SETTLEMENT_ELIGIBLE -> PAYMENT_RAIL_EXECUTION
      -> RECEIPT / DISPUTE / REFUND
```

Every transition must be authenticated and auditable. A security alert alone never authorizes payment or remote repair. No provider should receive remote shell, camera, microphone, account, or firmware access unless a separate explicit authorization grants the minimum necessary scope.

## Evidence and acceptance

Each task must define measurable acceptance criteria before work begins. Evidence may include signed test results, hashes, version measurements, logs with secrets redacted, and a customer confirmation. Evidence must be reproducible where possible and bound to the work-order ID. A content hash does not establish the truth of a report; independent review and trusted collection paths may be needed.

Do not reward a provider for generating alerts, increasing reported attack severity, or recommending unnecessary work. Separate detection from commercial approval; log conflicts of interest; cap spending; and require human confirmation for high-impact actions.

## Settlement adapter contract

Before connecting any payment rail, implement a dry-run adapter with explicit inputs:
- accepted work-order ID;
- evidence bundle digest;
- acceptance decision and approver;
- amount and asset;
- destination identity/address from a trusted source;
- idempotency key;
- policy version and expiry.

It must produce a deterministic **settlement proposal**, not send funds. The proposal is invalid if work is not accepted, the order is expired, amount exceeds its cap, the destination changed without reapproval, the idempotency key was reused for different terms, or required evidence is missing.

Real settlement requires a separately reviewed adapter, key custody design, fee handling, refund/dispute procedure, regulatory/legal review where applicable, and explicit user confirmation. Do not store wallet private keys in certificate claims, logs, source control, or ordinary TV storage.

## Required tests

Unauthorized work order, expired order, changed amount/destination, duplicate settlement request, missing acceptance, invalid provider signature, conflict of interest, evidence digest mismatch, customer rejection, cancellation, refund path, provider unavailability, payment adapter failure, and idempotent retry.

## Economic policy

Pricing, node compensation, shared-work allocation, fees, currency choice and distribution remain pending the project's explicit business-model consensus. This document intentionally defines no economic percentages or real-payment execution.
