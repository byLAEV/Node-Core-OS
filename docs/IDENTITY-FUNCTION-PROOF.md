# Identity Function Proof, Preference Propagation, and Consensus

**Status:** Architectural specification — future implementation  
**Version:** 0.1.0-draft  
**Scope:** Node Core OS identity activity, evidence, preference protocols, propagation, state recognition, and contextual reputation.

This document defines a conservative design contract. It does not claim that decentralized consensus, preference voting, identity health scoring, or network-wide evidence validation is already implemented. The current repository has a basic local evidence writer and IPFS content integration; the distributed protocol described here is a future layer.

## 1. Purpose

Node Core OS should let an identity demonstrate specific, verifiable activity without requiring a monetary payment or unnecessary disclosure of personal information. Evidence may be used by Node Core OS protocols and, when the identity chooses to present it, by external services.

The design must keep these concepts distinct:

- **Identity:** the key or identifier associated with an actor.
- **Activity:** an action performed under a protocol.
- **Evidence:** a record describing an activity and the checks applied to it.
- **Propagation:** delivery or availability of a record to other nodes.
- **Validation:** checking evidence against explicit protocol rules.
- **Consensus:** the mechanism used by participating nodes to recognize an agreed state.
- **Reputation:** a contextual interpretation of relevant, validated evidence.
- **Authorization:** a service-specific decision based on stated requirements.

A successful step must not be treated as proof of a different property. In particular, a preference submission does not by itself prove that a device is healthy, an identity is unique, an actor is human, or an actor is trustworthy for every purpose.

## 2. Core design principles

1. **No universal vote requirement.** Basic local storage and access to a person's own records must not be disabled merely because a person did not vote. A protocol may require current evidence only for functions whose documented purpose justifies it.
2. **No payment requirement for participation evidence.** The protocol must not require a monetary payment to create a valid participation record.
3. **Activity is not opinion.** Reputation for participation may reflect valid completion, not which preference was selected.
4. **Privacy by separation.** Identity authentication, eligibility, the selected preference, public propagation, and evidence presentation are separate concerns.
5. **Evidence is immutable in meaning.** Corrections or revocations append new records that reference the prior record; they do not silently rewrite history.
6. **Local storage and IPFS are complementary.** Local storage manages the node's operational state. IPFS content addressing identifies content and supports retrieval; a CID alone does not prove authorship, truth, consensus, or persistent availability.
7. **Consensus is explicit.** No implementation may claim network consensus until a specific algorithm, membership model, fault assumptions, quorum/finality rules, and recovery behavior are selected and tested.
8. **Graceful offline behavior.** A disconnected node must not be treated as malicious solely because it cannot propagate during an outage.
9. **Contextual reputation.** Reputation must be explainable through evidence types and rules. There is no universal trust score.
10. **Fail safely.** Missing or unverifiable evidence must be reported as unknown or insufficient, not fabricated as valid or automatically interpreted as malicious.

## 3. The protocol cycle

The planned identity activity cycle is:

~~~text
Protocol publishes a period and rules
                |
                v
Identity authenticates and checks eligibility
                |
                v
Identity performs a permitted preference activity
                |
                v
A participation record is created and validated locally
                |
                v
Record/content is propagated to peers
                |
                v
Peers independently verify signature, context, period and rules
                |
                v
The protocol's state-recognition mechanism resolves accepted records
                |
                v
A period result and/or evidence checkpoint is produced
                |
                v
Identity status is evaluated against the applicable freshness policy
                |
                v
Only functions requiring current evidence apply that requirement
~~~

This is a protocol lifecycle, not a claim that all steps already run in the current program.

## 4. Preferences and their outcomes

A preference protocol must publish a versioned definition before opening a period. At minimum, it defines:

- stable protocol and poll identifiers;
- opening and closing time, in UTC;
- eligible identity/key rules;
- selection mode: single choice, multiple choice, approval, ranking, or score;
- whether preferences are public or secret;
- whether identity references are public or pseudonymous;
- duplicate-submission and replacement rules;
- validation rules and their version;
- tally method, tie handling, and minimum participation conditions;
- propagation and closure policy;
- retention and privacy policy.

A protocol may produce two distinct outputs:

1. **Collective output:** a deterministic tally or preference result derived from the accepted submissions.
2. **Individual output:** evidence that a specific identity completed a valid participation action for that period.

The individual evidence must not disclose the selected preference unless the published protocol explicitly requires public choices and the participant has been informed. A participation credential should preferably prove completion without carrying the preference value.

A protocol must define whether a participant may replace a submission before the closing time. If replacement is allowed, only the protocol-defined final submission counts; earlier submissions remain auditable but must not be counted twice. After closure, the accepted set and tally rules are fixed by a closure record.

A vote is not automatically a consensus message. A preference tally expresses participant choices. A consensus mechanism separately determines which records and closure state are recognized by the network.

## 5. Propagation and validation

Propagation has several distinct levels and must not be represented by one ambiguous boolean:

- **created:** a local record was written;
- **locally_validated:** local deterministic checks passed;
- **submitted_for_propagation:** the node attempted to publish or send the content;
- **peer_observed:** one or more identified peers acknowledged or returned the content;
- **available_under_policy:** the protocol's stated availability condition was met;
- **recognized_in_state:** the state-recognition mechanism included the record in an accepted checkpoint;
- **finalized:** the selected consensus mechanism's documented finality condition was met.

The protocol must not label content globally propagated just because it was added to a local Kubo repository. If the implementation cannot verify a propagation level, it must report the level as unknown.

Each receiving node independently checks at least:

1. schema and protocol version;
2. required fields and valid time interval;
3. content integrity;
4. signature against the referenced public key or credential;
5. period and poll identifiers;
6. eligibility and duplicate/replacement rules;
7. validation policy version;
8. replay protection and whether the record has already been processed;
9. any revocation or superseding record that applies.

A valid CID only identifies the bytes. Authentication and protocol acceptance require these additional checks.

## 6. Consensus contract

Before selecting a consensus algorithm, the project must define the network assumptions. These include whether participants are permissionless or have known membership, whether Sybil resistance exists, what fraction of nodes may be faulty, whether network partitions are expected, and what finality guarantees applications need.

The implementation must then specify:

- how nodes join and leave the participating set;
- what constitutes a proposal or candidate state;
- which records are eligible for inclusion;
- how conflicting records are resolved;
- quorum or weight calculation, if applicable;
- how duplicate identities and Sybil attacks affect participation;
- timeout, retry, partition, and recovery behavior;
- how nodes identify a finalized checkpoint;
- how a new node synchronizes and verifies historical state;
- how protocol upgrades are versioned and accepted.

Do not use simple majority of network connections as a substitute for Sybil resistance. One operator may control many nodes. Do not equate a preference majority with consensus finality. Do not invent quorum percentages until the threat model and membership model are documented.

Until these decisions are made and implemented, use wording such as **proposed state-recognition mechanism** or **consensus design**, not “consensus implemented.”

## 7. Identity Function Proof (IFP)

“Identity Function Proof” (IFP) is the provisional name for the proposed periodic activity protocol. It is not classical proof of work: it does not claim to prove a quantity of computational work. Its purpose is to provide evidence that a defined protocol activity was completed.

An IFP policy must specify:

- activity type and protocol version;
- period identifier and validity interval;
- the exact completion condition;
- identity authentication and eligibility checks;
- required evidence and signature checks;
- propagation level required, if any;
- evidence freshness duration;
- a grace period for connectivity or device interruptions;
- affected capabilities if evidence expires;
- recovery or renewal procedure;
- privacy and retention requirements.

### Status model

The status of an identity's activity evidence should be derived from records and policy, not manually asserted without support.

- **unknown:** no applicable evidence can be verified;
- **current:** valid evidence satisfies the freshness policy;
- **renewal_due:** the current evidence is nearing expiry;
- **grace:** the normal deadline passed, but the configured grace period remains;
- **expired:** no current evidence satisfies the policy after grace;
- **revoked:** a valid revocation or superseding policy record applies;
- **verification_pending:** necessary checks cannot yet be completed.

The exact time limits are policy values, not universal constants. The implementation must use UTC timestamps, handle clock skew explicitly, and avoid treating a local clock alone as authoritative consensus time.

### Capability effects

Expiration must not delete an identity or erase its historic evidence. It may disable only capabilities that explicitly require current IFP evidence. Personal data access, local export, recovery, and viewing historical evidence should remain available unless a separate security requirement justifies a restriction.

A failed renewal means “current activity not demonstrated under this policy”; it does not automatically mean fraud, a bot, or a malicious node.

## 8. Coherence, constancy, and node health

These are separate dimensions and must be measured only with suitable evidence.

- **Coherence:** records have valid structure, signatures, references, ordering, and no unresolved contradictions under the protocol's rules.
- **Constancy:** the identity has completed qualifying activities across multiple defined periods.
- **Availability:** a node or service responded to a defined challenge or request within the stated time and observation conditions.
- **Propagation reliability:** records reached the required peers or availability target under a measurable policy.
- **Identity uniqueness / humanity:** not established by periodic preference participation alone; it requires a separate, explicitly justified mechanism if a use case needs it.

Do not collapse these dimensions into a single “healthy human identity” assertion. A health summary should list the checks performed, their time, their sources, and unknown or failed checks. Constancy should be described as a history, not as proof of truthfulness.

## 9. Evidence record

The first implementation should use a versioned JSON schema and deterministic validation. The following is illustrative, not yet a repository API contract:

~~~json
{
  "schema": "node-core.identity-function-evidence",
  "schema_version": "0.1.0",
  "evidence_id": "implementation-generated-id",
  "identity_ref": "identity-key-or-canonical-reference",
  "activity": {
    "protocol_id": "node-core.preferences",
    "poll_id": "poll-reference",
    "period_id": "period-reference",
    "activity_type": "valid_participation"
  },
  "timestamps": {
    "created_at": "2026-10-09T12:00:00Z",
    "valid_from": "2026-10-09T00:00:00Z",
    "valid_until": "2026-10-16T00:00:00Z"
  },
  "validation": {
    "policy_version": "0.1.0",
    "status": "locally_validated",
    "checks": [
      "schema",
      "signature",
      "period",
      "duplicate_policy"
    ]
  },
  "content": {
    "cid": null,
    "previous_evidence_ref": null
  },
  "signature": {
    "algorithm": "defined-by-identity-key-profile",
    "value": "implementation-generated-signature"
  }
}
~~~

Placeholder values above are not valid cryptographic material. A production schema must define the canonical serialization and signature algorithm, reject unknown critical fields, and test signature verification. Do not sign an ordinary JSON string unless canonicalization is specified.

For private preference ballots, the public evidence should not include the selected choice. The identity-to-participation link may also need selective disclosure or a pseudonymous reference, depending on the privacy mode.

## 10. Reputation and third-party use

Evidence can contribute to a contextual reputation statement only if the consumer can inspect the evidence type, issuer/identity binding, validation policy, time interval, and provenance.

A relying service must define its own policy, such as “at least one valid participation in the last N periods” or “a signed availability check passed during the last interval.” It must not treat participation as proof of technical competence or universal trust.

The system should prefer explainable claims over an unexplained score. If a score is introduced later, its inputs, weights, expiry, uncertainty, and appeal/correction path must be documented. A participant's selected option must not increase or decrease activity reputation.

The identity controls presentation of personal evidence. Propagation, public publication, and third-party presentation are separate operations.

## 11. Threats and required mitigations

| Threat or failure | Required design response |
|---|---|
| Duplicate submission | Stable period and identity keys; deterministic duplicate/replacement rule; replay protection. |
| Sybil identities | Explicit threat model and separate Sybil-resistance policy; never assume voting prevents Sybils. |
| Automated participation | Treat as valid automation unless a use case requires a separate anti-abuse check; participation alone does not prove humanity. |
| Forged evidence | Cryptographic signature and identity binding; strict schema validation. |
| Content available only locally | Report local-only status; pin/replicate according to a defined availability policy. |
| Conflicting closure records | Deterministic conflict rules and consensus/finality mechanism. |
| Offline identity | Grace and renewal; do not infer malicious intent from a missed period alone. |
| Privacy leakage | Separate ballot from participation credential; data minimization and selective disclosure. |
| False health claim | Report each verified dimension separately; unknown is not healthy. |
| Historical correction | Append signed revocation/superseding record; preserve audit trail according to retention policy. |
| Clock manipulation | Use period rules and accepted checkpoint/order; define skew tolerance and avoid relying only on local wall clock. |
| Reputation laundering | Preserve provenance, evidence type, time, and context; avoid universal trust scores. |

## 12. Phased implementation plan

### Phase 0 — Specification and threat model

- Review existing identity, evidence, content, IPFS, and reputation code.
- Freeze terminology and the distinction between implemented and planned behavior.
- Define the first use case and threat model.
- Approve JSON schemas, privacy mode, time windows, and duplicate rules.

**Exit criteria:** a reviewed specification and machine-readable schema; no claims of network consensus.

### Phase 1 — Local evidence MVP

- Add a pure validation module with no network dependency.
- Validate schema, timestamps, required references, duplicate keys, and status transitions.
- Add deterministic unit tests for valid and invalid evidence.
- Preserve compatibility with the existing local evidence writer.

**Exit criteria:** tests pass locally and in GitHub Actions; invalid evidence is rejected with actionable errors.

### Phase 2 — Preference-period simulator

- Implement poll definition and period records.
- Validate submissions, duplicate/replacement rules, closing conditions, and deterministic tallying.
- Generate separate aggregate-result and individual-participation evidence records.
- Test that a choice does not affect participation reputation.

**Exit criteria:** same accepted submission set always yields the same result; duplicate and late submissions follow documented rules.

### Phase 3 — IPFS content transport

- Store canonical evidence content locally.
- Add content to Kubo and record its CID.
- Distinguish local storage, local pinning, attempted publication, peer observation, and consensus recognition.
- Test Kubo-unavailable, pin failure, retry, retrieval, and content-integrity scenarios.

**Exit criteria:** the program never reports network propagation or consensus based only on a local CID.

### Phase 4 — Multi-node propagation

- Define peer discovery and authenticated node communication.
- Verify evidence independently on receiving nodes.
- Add replay protection, retry, offline recovery, and peer-diversity measurements.
- Test at least two independent nodes and partition/recovery scenarios.

**Exit criteria:** receiving nodes can independently verify the same evidence and report their actual propagation state.

### Phase 5 — Consensus and closure

- Select an algorithm only after documenting membership, Sybil assumptions, fault model, quorum, and finality.
- Define accepted checkpoints and conflict resolution.
- Test equivocation, concurrent closure, restart, partition, and synchronization of a new node.

**Exit criteria:** documented finality guarantees are demonstrated by tests; until then, the feature remains experimental.

### Phase 6 — Freshness, reputation, and authorization

- Derive current/renewal_due/grace/expired status from verified records and policy.
- Add contextual evidence queries and explainable reputation claims.
- Restrict only the capabilities that explicitly require current evidence.
- Test renewal, grace, recovery, privacy, and third-party verification.

**Exit criteria:** expired evidence never deletes history; services can explain exactly which rule allowed or denied a capability.

## 13. Minimum acceptance test matrix

The implementation is not ready for production until tests cover at least:

1. Valid signed evidence is accepted.
2. Missing required fields are rejected.
3. Invalid signature is rejected.
4. Evidence from a different poll or period is rejected for the current period.
5. Duplicate submissions cannot inflate the tally.
6. Late submissions follow the published closing policy.
7. Tally output is deterministic for the same accepted set.
8. Individual participation evidence does not expose a secret choice.
9. Local CID creation is not reported as peer propagation.
10. Kubo outage leaves evidence in a recoverable pending state.
11. Expired evidence changes applicable status without deleting history.
12. Grace-period behavior is deterministic.
13. A new valid participation renews evidence under policy.
14. A missed period alone does not label the identity a bot or malicious.
15. Reputation derived from participation does not depend on selected preference.
16. A third party can verify the evidence and its policy version.
17. Unknown or unverifiable evidence is not reported as healthy.
18. Two nodes agree on the finalized state only according to the selected and tested consensus mechanism.
19. A network partition does not produce an unsupported claim of global finality.
20. A node recovering after disconnection can resynchronize and validate checkpoints.

## 14. Repository status and next action

The current repository already has a basic node_core/evidence.py text-evidence writer and content/IPFS integration. The identity package and reputation package are present, but this document does not assume they implement the distributed protocol described above.

The next implementation change should be limited to **Phase 1: local evidence schema and deterministic validation**, with unit tests. Do not implement a pretend consensus engine, network-wide health score, Sybil resistance, or production identity uniqueness before the relevant requirements and threat models exist.

The implementation must preserve the project's existing terminal-first, user-owned storage approach and must not modify the installer or Kubo lifecycle as part of this protocol work.
