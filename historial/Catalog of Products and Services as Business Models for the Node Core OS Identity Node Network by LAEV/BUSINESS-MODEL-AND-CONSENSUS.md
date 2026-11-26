# Business Model and Economic Consensus

**Status:** `pending-consensus`  
**Applies to:** All products in this catalog  
**Prices and distribution formula:** Not defined

## 1. Commercial model

Node Core OS byLAEV may offer enterprise and institutional customers defined security services delivered by authorized personal and technical identities participating in the distributed identity-node network. A customer purchases an agreed deliverable—not a guarantee of invulnerability.

Work may include assessment planning, test execution, evidence collection, independent verification, monitoring, reporting, and coordinated multi-node tasks. The specific work allowed depends on the product specification and customer authorization.

## 2. Roles and separation of duties

- **Customer:** owns or is authorized to test the target, defines objectives, and accepts the contract scope.
- **Coordinator:** creates the work order and distributes authorized subtasks.
- **Provider node:** executes an assigned task and submits evidence.
- **Verifier:** checks evidence against acceptance criteria; independence requirements should be defined for each risk level.
- **Issuer:** signs the certificate after the required review and approval process.
- **Settlement component:** records accepted work and executes payments only after the economic rules and payment implementation are approved.

One entity may hold multiple roles only when allowed by the policy and disclosed. High-risk assessments should avoid having the same party perform, verify, and approve its own work.

## 3. Work lifecycle

1. Register a customer request and confirm authorization.
2. Create a versioned work order with scope, deadline, inputs, acceptance criteria, and budget if one is approved.
3. Select eligible providers under the applicable protocol.
4. Execute the task in the permitted environment.
5. Submit signed or otherwise authenticated evidence and reproducible artifacts.
6. Validate the result, check duplication and conflicts of interest, and accept, reject, or request correction.
7. Issue or update the certificate record if the service's requirements are satisfied.
8. Record the accepted contribution and any dispute.
9. Calculate and settle payment only according to a separately approved economic policy.

## 4. Questions reserved for consensus

The consensus process must define:
- eligibility for proposing, performing, verifying, and approving work;
- how customer demand and budgets are represented;
- technical work units for each service;
- evidence authenticity and acceptance;
- contribution attribution for individual and joint work;
- pricing, fees, costs, reserves, and distribution;
- payment asset or method, settlement finality, idempotency, and reconciliation;
- appeals, corrections, fraud handling, and dispute resolution;
- anti-Sybil and anti-collusion rules;
- conflicts of interest and independent assessment;
- governance, quorum, versioning, and activation of policy changes;
- privacy, retention, tax, contract, and other legal obligations.

No answer or numeric value is implied by this document. The approved decision must be versioned, attributable, and linked from the catalog.

## 5. Principles for fair attribution

- Do not reward raw identity or node count.
- Do not treat a heartbeat or an unverified assertion as proof of a completed service.
- Do not equate compute effort with correctness of the result.
- Avoid double payment for the same work order or duplicated evidence.
- Record both the individual tasks and the joint deliverable when multiple nodes cooperate.
- Provide a dispute path for incomplete, rejected, or contested work.
- Separate certificate validity and service quality from the amount paid.
- Never make the purchase of a certificate a guarantee of favorable findings.

## 6. Payment activation gate

Real payments must remain disabled until there is an approved economic policy and an implementation with tests for authorization, replay protection, duplicate settlement, auditability, reconciliation, disputes, key management, failure recovery, and applicable legal obligations. A passing documentation or certificate-format test does not satisfy this gate.
