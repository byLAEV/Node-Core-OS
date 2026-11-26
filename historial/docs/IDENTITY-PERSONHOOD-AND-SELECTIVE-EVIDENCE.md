# Personhood Verification, Evidence Categories, and Selective Disclosure

**Status:** Architectural specification — planned, not implemented  
**Version:** 0.1.0-draft  
**Related specification:** [Identity Function Proof, Preference Propagation, and Consensus](IDENTITY-FUNCTION-PROOF.md)

This document extends the Identity Function Proof (IFP) design. It defines the intended relationship between sustained identity activity, protocol-based checks that assess whether an identity corresponds to a real person, individual evidence categories, and selective disclosure using zero-knowledge proofs (ZKPs).

It is a design contract, not a claim that personhood verification, distributed consensus, a credential catalogue, or ZKP presentation is implemented in Node Core OS.

## 1. Architectural intent

Node Core OS should accumulate a verifiable history for an identity and, at defined moments, use specific protocol procedures to assess whether that identity corresponds to a real person and whether the person/identity remains active under the protocol's rules.

The model has two related but distinct dimensions:

1. **Personhood assessment:** evidence produced by a defined human-verification or personhood-accreditation procedure, with explicit assurance limits.
2. **Constancy and protocol activity:** evidence that the identity has completed qualifying activities across defined periods, including eligible preference participation, propagation, and records recognized by the network's state-recognition or consensus mechanism.

A sustained activity history can strengthen continuity evidence and support periodic re-checks. However, activity alone cannot prove personhood: bots can automate actions, and one person or operator may control multiple identities. The network may report an identity as **verified as a real person under a named policy** only when an explicit personhood procedure has passed and its result is valid. The status must identify the policy and its limitations; it must not claim infallible or universal proof.

The protocol may combine repeated activity, challenge-response, trusted credentials, privacy-preserving checks, and duplicate/Sybil-risk controls. The exact combination must be selected for the required assurance level and documented before implementation.

## 2. Independent results

These results must not be collapsed into one boolean or score:

- **Identity exists:** a technical identity reference/key is present.
- **Personhood verified under policy:** a named procedure produced a valid result binding the identity to a real person under that procedure's stated assurance.
- **Recent human check:** a defined check was completed within a stated time window. It does not automatically mean the person is currently online.
- **Constancy verified:** qualifying activities exist across the required periods under the activity policy.
- **Node availability:** a node answered a specified technical challenge/request under measured conditions.
- **Propagation recognized:** evidence reached the policy-defined peers or checkpoint.
- **Consensus/state accepted:** a record or checkpoint was accepted by the specified state-recognition protocol.
- **Credential valid:** a particular credential's issuer, signature, scope, validity, and revocation status passed its own verification rules.

Passing one check must not silently imply that the other results passed.

## 3. Personhood-check protocol

Any procedure intended to assess whether an identity corresponds to a real person must have a versioned policy that specifies:

1. The claim being assessed and intended assurance level.
2. Eligibility and identity-binding rules.
3. The procedure used, such as an approved credential, challenge-response, or another defined mechanism.
4. What evidence is collected and what is deliberately not collected.
5. How automated responses, replay, impersonation, and duplicate identities are mitigated.
6. Whether a third-party issuer or verifier is trusted and how that trust is configured.
7. Validity period, renewal schedule, grace period, revocation, appeal, and recovery.
8. Behavior for offline users, accessibility needs, lost devices, and incomplete checks.
9. Data retention, disclosure, and privacy rules.
10. Evidence records and verification steps independent nodes can check.
11. Whether a result is local, issuer-attested, peer-observed, or recognized by network consensus.
12. Limits of the claim and residual Sybil/false-acceptance risks.

A periodic vote may be one activity or challenge in a personhood policy, but an ordinary preference ballot is not a human test by itself. Consensus can recognize the result of a procedure; consensus does not make a weak procedure a reliable personhood test.

The network must not infer fraud merely from a missed check. Proposed states include not assessed, verification pending, verified under policy, renewal due, grace, review required, expired, revoked, and unknown. A failed or expired check means the current policy's requirement has not been demonstrated; it does not by itself establish that the identity is fake.

Every verified-under-policy result must be traceable to a policy version, evidence reference, observation/issuance time, validity interval, and verification outcome. Sensitive proof material must not be published merely to make the status auditable.

## 4. Constancy and the longest valid evidence history

The identity's evidence history may accumulate records from qualifying activities, such as activity records for defined periods; participation evidence from preference protocols; propagation observations and acknowledgements; records accepted into recognized checkpoints; consensus/finality checkpoints once a specific mechanism exists; and personhood-check results with their renewals or revocations.

The **longest valid history** may be used as a temporal reference for comparing constancy, provided records satisfy applicable validation and acceptance rules. It is a measurement reference, not a rule that makes the longest branch true merely because it is longer.

The protocol must distinguish:
- number of qualifying periods with evidence;
- elapsed time between verified checkpoints;
- continuity and gaps;
- valid activity events;
- propagation level and accepted checkpoint;
- personhood assessments and their validity windows;
- current evidence freshness;
- count and size of evidence content.

File size, repeated records, repeated votes, or arbitrary extra records must not inflate constancy. Each period/activity needs deterministic uniqueness, replay protection, and qualification rules. Gaps must remain visible and must not be silently counted as continuous activity. Local timestamps or a CID alone do not establish trusted historical time or network acceptance.

A relative duration such as identity duration divided by longest accepted duration may be reported as a descriptive temporal ratio. It must not be described as a universal trust score or as a probability that a person is real. The reference history itself must be accepted under validation, fork-resolution, and finality rules.

The network may include personhood evidence in the history, but must not infer a valid personhood result from history length alone. A personhood result must come from a qualifying personhood procedure and remain bounded by its validity/revocation rules.

## 5. Activity, preferences, propagation, and consensus

Different activities provide different evidence:

- A valid preference submission can evidence completion of a defined participation action.
- A preference tally expresses collective choices under published tally rules.
- Propagation evidence can show that content was observed or acknowledged at specified peers.
- A consensus checkpoint can show that a record/state was recognized according to the selected algorithm and finality rules.
- A personhood procedure can support a personhood claim only to the extent guaranteed by that procedure.

The individual participation output and collective tally output must remain separate. Participation reputation must not depend on which option was selected. Secret preferences must not be exposed by participation evidence unless the protocol explicitly defines a public ballot and informs participants.

Consensus is a separate state-recognition mechanism; it is not synonymous with a preference majority. No claim of distributed acceptance or finality may be made before the membership model, Sybil assumptions, fault model, quorum/finality rules, and recovery behavior are implemented and tested.

## 6. Individual evidence catalogue and labels

An identity may maintain a catalogue of individual evidence references grouped by user-meaningful labels. Initial example categories include:

- professional
- cultural
- family
- intimate
- health
- sports
- academic
- financial
- citizenship
- identity activity

The list is illustrative and must be extensible. Labels are classification metadata; a label alone does not prove that a claim is true. Each evidence item needs a defined issuer/source, claim, identity binding, integrity/authentication mechanism, validity interval, revocation/supersession policy, and verification rules appropriate to that category.

The protocol must distinguish the label/category; the claim; issuer or origin; credential/evidence bytes or protected reference; integrity and signature verification; expiry and revocation; privacy classification; verification status and policy; and what a relying service is allowed to learn.

A long activity history does not automatically validate a professional, family, health, financial, or other personal claim. Every credential must be checked according to its own issuer and validity policy.

## 7. Zero-knowledge proofs and selective disclosure

A zero-knowledge proof (ZKP) may allow an identity to demonstrate a defined property of a credential or evidence without disclosing the full underlying information. This is future work and requires selecting a suitable, reviewed cryptographic protocol and credential format.

Potential examples include proving possession of a valid credential issued by an accepted issuer; satisfaction of a threshold or eligibility condition; that a credential is within its validity period; or that a policy-defined activity condition was met, if the evidence structure and proof system support the statement.

A ZKP does not by itself prove that the original claim is true, that an issuer is trustworthy, that a human is unique, or that a credential has not been revoked. Those properties require sound credential issuance, identity-binding, revocation, and verification design.

The relying service should receive the minimum information needed. A proof should be bound to the verifier's challenge, intended audience, requested claim, and freshness requirements to prevent replay or use in another context. The verifier must validate issuer trust and revocation policy where applicable.

## 8. Privacy and storage boundaries

Local storage and Kubo/IPFS can complement each other, but IPFS is content-addressed distribution/retrieval, not access control or confidentiality. A CID does not make private content private.

Recommended defaults:
- keep private source records and sensitive personal evidence under user-controlled local storage or encrypted storage;
- publish only content intended for public distribution;
- encrypt sensitive content before distributed storage, with keys controlled separately;
- avoid putting health, intimate, family, or other sensitive category labels in public manifests when the label itself leaks information;
- prefer a minimal proof or privacy-preserving reference rather than the underlying personal record;
- document key backup, rotation, revocation, recovery, and deletion limitations;
- treat metadata, access patterns, CID links, and identity references as potential privacy leaks.

Revocation of a credential or reference does not guarantee erasure of copies already distributed through IPFS. The protocol must not promise deletion from the network unless it can actually guarantee that outcome.

## 9. Contextual evaluation and third-party use

A third-party service must state which claim it needs and what assurance it accepts. It may require a current professional credential, a personhood check under a specified policy, or a defined activity period. It should not request the complete identity history by default.

Do not create one universal score that mixes personhood, node availability, constancy, professional credentials, health, family status, and preferences. Keep dimensions separate and provide an explainable verification result that includes policy, scope, time, source, and limitations.

The user should control whether personal evidence is presented, except for narrowly documented protocol operations necessary to operate the network. Failure to vote or participate must not remove access to personal data, export, recovery, or historical records. Any capability gated by fresh evidence must be explicitly justified and documented.

## 10. Threats and acceptance requirements

Tests must cover at least:

1. A technical identity with no personhood check remains not assessed, regardless of activity duration.
2. A successful personhood procedure produces only a policy-scoped result with a validity interval.
3. A missed periodic check does not automatically mark an identity fake or malicious.
4. An expired or revoked personhood result is not presented as current.
5. Replayed challenges and evidence are rejected.
6. Multiple identities controlled by one operator are considered in the Sybil threat model.
7. A bot completing an ordinary preference submission is not automatically classified as a verified human.
8. A preference selection does not change participation evidence or activity reputation.
9. A local CID does not imply peer propagation or consensus acceptance.
10. The longest history is computed only from qualifying, validated records and accepted checkpoints.
11. Duplicate records, oversized records, and repeated submissions cannot inflate constancy.
12. Missing periods are visible and do not count as continuous activity.
13. Personhood results, activity evidence, and node availability remain separate metrics.
14. A category label alone cannot pass credential verification.
15. A credential with invalid signature, untrusted issuer, expired validity, or applicable revocation is rejected.
16. A selective-disclosure proof is bound to verifier, challenge, claim, and freshness requirements.
17. Public manifests do not expose sensitive labels or personal records by default.
18. The implementation does not claim that a ZKP independently establishes the truth of an underlying claim.
19. History length does not automatically authorize professional, health, financial, or other claims.
20. A relying service can identify the policy and exact evidence supporting its decision.

## 11. Implementation roadmap

1. **Specification:** agree on the personhood claim, assurance model, threat model, status vocabulary, evidence categories, and privacy defaults.
2. **Local schema:** add explicit typed records for activity evidence, personhood assessments, and individual credentials. Validate structure and time semantics without pretending to verify cryptography.
3. **Policy-bound verification interfaces:** define interfaces and tests for signature/issuer verification, challenge freshness, revocation, and identity binding before selecting cryptographic dependencies.
4. **History metrics:** calculate deterministic constancy metrics only from qualifying validated records; expose gaps and provenance.
5. **Preference simulator:** separate aggregate tally from individual participation evidence and keep private choices out of participation credentials.
6. **Multi-node propagation and consensus:** implement only after peer authentication, Sybil assumptions, state-recognition algorithm, and finality model are specified.
7. **Credential catalogue:** add category labels and per-credential validity/revocation policies, with private-by-default handling for sensitive categories.
8. **ZKP integration:** select an established, reviewed scheme and implement challenge-bound selective disclosure with tests for replay, revocation, and verifier binding.
9. **Third-party verification:** publish contextual verification results rather than a universal reputation score.

Until relevant phases are implemented and tested, the repository must describe them as planned capabilities.

## 12. Status boundary

This document does not implement personhood verification, anti-Sybil guarantees, distributed consensus, credential issuance, selective disclosure, or ZKP cryptography. The existing local evidence validator checks record structure and timestamp semantics only. It does not cryptographically verify signatures or prove that a record was propagated, accepted by consensus, or created by a real person.
