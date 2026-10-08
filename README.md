# Node Core OS

**Node Core OS** is a personal infrastructure designed to give a person or entity its own digital core from which to preserve, manage, verify, corroborate, and use digital resources, identity, records, evidence, and, progressively, reputation.

The project starts from a fundamental premise:

> **A person should have access to their own infrastructure before depending on external applications, services, or systems to represent who they are, what they have done, what they do, or what they intend to do.**

Node Core OS manages two fundamental storage domains:

- **Local storage** — resources preserved directly on the Node.
- **Decentralized storage** — resources managed through technologies such as Kubo/IPFS.

Distributed and decentralized protocols, services, and applications can progressively operate on top of these storage foundations.

Node Core OS is therefore not merely a file-storage system.

Its long-term objective is to provide a **personal infrastructure for records, evidence, identity, corroboration, reputation, protocols, and participation**, while preserving the person's ability to decide what to record, why it should be recorded, what should be corroborated, what may be shared, and when information should be used.

---

# 1. Fundamental Idea

Node Core OS is not conceived primarily as an application.

It is conceived as a **personal infrastructure and digital core**.

The fundamental relationship is:

```text
PERSON
  │
  ▼
NODE CORE OS
  │
  ├── Local Storage
  ├── Decentralized Storage
  ├── Records
  ├── Evidence
  ├── Identity
  ├── Corroboration
  ├── Reputation
  ├── Protocols
  └── Applications
```

The infrastructure should exist before applications determine how it is used.

Therefore:

> **Node Core OS does not intend to define in advance what a person must do. It intends to provide a place from which the person can decide what to do.**

---

# 2. The Person as the Core

The Node exists to serve the person or entity that chooses to use it.

The infrastructure should provide continuity for information that the person considers important, including:

- who they are;
- which identifiers they use;
- which records they have created;
- which facts they can substantiate;
- which activities they have performed;
- which relationships they have established;
- which knowledge or capabilities they can demonstrate;
- what reputation they have built in particular contexts;
- what they intend to do in the future.

This does not mean that Node Core OS should publish all of this information.

On the contrary:

> **Preservation does not mean publication. Recording does not mean sharing. Possessing evidence does not mean being obligated to disclose it.**

The person should retain control over how records are used.

---

# 3. Request-Driven Operation

One of the fundamental principles of Node Core OS is:

> **The system should not autonomously decide to represent, propagate, evaluate, or use personal information when doing so affects the person's agency. Such operations should originate from an explicit request or a defined authorization.**

A request is therefore a fundamental unit of the system.

A conceptual interaction may look like:

```text
PERSON
  │
  │ "I need to create an evidence record"
  ▼
REQUEST
  │
  ▼
NODE CORE OS
  │
  ├── determines what information is required
  ├── records the requested data
  ├── preserves the evidence
  ├── requests corroboration when appropriate
  └── prepares the result
  │
  ▼
RESULT
  │
  ▼
PERSON
  │
  └── decides whether to use, share, or preserve it
```

A request may define:

- actor;
- intention;
- purpose;
- context;
- scope;
- duration;
- required information;
- required evidence;
- required corroboration;
- storage policy;
- privacy posture;
- expected result.

The request expresses **what the person wants to accomplish**.

Applications may generate requests, but they should not thereby receive unrestricted access to the Node.

---

# 4. Forget / Remember Context Model

Node Core OS distinguishes between **preserving historical information** and **actively using that information as context**.

> **To forget is to stop considering historical context by default. To remember is to selectively apply historical context when a present requirement requires it.**

A Node may retain records, evidence, identity information, credentials, reputation history, and other historical data while entering a state in which that history is **not actively applied to the current context**.

Conceptually:

```text
                     NODE
                       │
                       ▼
                  PRESENT STATE
                       │
                       ▼
                   FORGOTTEN
                       │
          historical context is
          not applied by default
                       │
                       ▼
              CURRENT REQUIREMENT
                       │
                       │ requires historical evidence?
                       ▼
                    REMEMBER
                       │
                       ▼
             RELEVANT MEMORY ONLY
                       │
                       ▼
               CURRENT DECISION
```

## 4.1 Forgotten Does Not Mean Deleted

The `FORGOTTEN` state does not imply that information has been destroyed.

It means that historical information is not automatically incorporated into the active context of the Node.

Therefore:

```text
FORGOTTEN
    ≠
DELETED
```

and:

```text
PRESERVED
    ≠
ACTIVELY USED
```

This distinction is fundamental to Node Core OS.

A Node may preserve information for continuity, evidence, integrity, auditability, or future requirements while not using that information to define the Node's current state.

## 4.2 The Present Is the Default Context

Node Core OS should evaluate the current state of a Node from its **present context** by default.

Historical information should not automatically become a permanent representation of the current state.

```text
CURRENT STATE
    =
CURRENT EVIDENCE
    +
CURRENT CONDITIONS
```

rather than:

```text
CURRENT STATE
    =
CURRENT CONDITIONS
    +
ENTIRE HISTORICAL RECORD
```

The past remains available, but it is not presumed to be relevant to every present operation.

> **The Node is considered according to what is relevant now. Its history becomes relevant when a current requirement makes it relevant.**

## 4.3 Remember Is Requirement-Driven

`REMEMBER` is not intended to mean:

> "Load everything this Node has ever been."

Instead, `REMEMBER` means:

> **"Apply the historical context necessary to evaluate a specific present requirement."**

A request may therefore cause a selective memory operation:

```text
REQUEST
   │
   ▼
REQUIREMENT
   │
   ▼
Does the requirement require historical context?
   │
   ├── NO ──► Continue using present context
   │
   └── YES
          │
          ▼
       REMEMBER
          │
          ▼
   Relevant historical evidence
          │
          ▼
    Requirement evaluation
```

The requirement determines the scope of the memory that needs to be considered.

For example:

```text
Requirement:
"Does this Node possess credential X?"
```

does not necessarily require:

```text
All identity history
All reputation history
All records
All previous activities
```

It may require only:

```text
Credential X
+
Proof of validity
+
Proof of association
```

This makes memory **requirement-driven rather than globally active**.

## 4.4 Selective Memory

Node Core OS should prefer the smallest historical context necessary to satisfy a requirement.

```text
ENTIRE HISTORY
      │
      │ requirement
      ▼
RELEVANT HISTORY
      │
      ▼
REQUIRED EVIDENCE
      │
      ▼
CURRENT DECISION
```

This creates an architectural distinction between:

```text
Memory Available
```

and:

```text
Memory Applied
```

The existence of historical information does not by itself authorize its use.

## 4.5 Memory, Identity, and Reputation

This model also separates three concepts that should not be treated as equivalent:

```text
IDENTITY
   │
   └── Who or what is being represented?

HISTORY
   │
   └── What has been recorded about that identity?

REPUTATION
   │
   └── What can be inferred from relevant evidence
       within a particular context?
```

A Node does not automatically receive its entire historical reputation whenever it enters the system.

Instead:

```text
NODE
  │
  ▼
PRESENT
  │
  ▼
FORGOTTEN
  │
  ▼
CURRENT REQUIREMENT
  │
  ▼
REMEMBER
  │
  ▼
RELEVANT HISTORY
  │
  ▼
CONTEXTUAL REPUTATION
```

Reputation can therefore remain historical evidence without becoming a permanent and universal label.

## 4.6 Forgetting as Context Control

The `FORGOTTEN` state should be understood as a **context-control mechanism**, not as a data-destruction mechanism.

It allows Node Core OS to distinguish:

```text
STORE
   ≠
REMEMBER
   ≠
USE
   ≠
SHARE
   ≠
PUBLISH
   ≠
AUTHORIZE
```

These operations may have different requirements, permissions, scopes, and lifetimes.

A record may remain stored while being:

- forgotten from the active context;
- unavailable to a particular application;
- restricted to a particular requirement;
- selectively recalled;
- used only to generate a proof;
- or, when required by a specific policy, actually deleted or anonymized.

Therefore, Node Core OS should not treat "forgetting" and "deletion" as synonymous operations.

## 4.7 The Right to Forget Without Necessarily Erasing

This architecture provides a technical interpretation of an important distinction related to the concept of a **right to forget**:

> **Forgetting can mean ceasing to actively use historical information, rather than necessarily destroying every underlying record.**

This is an architectural principle, not a universal legal definition of a right to erasure or right to be forgotten.

Where a legal, contractual, security, or policy requirement requires actual deletion, anonymization, restriction, or retention, Node Core OS must be capable of applying that separate policy.

The architectural distinction is therefore:

```text
FORGET
    │
    └── stop applying historical context

RESTRICT
    │
    └── prevent specified uses of historical context

PURGE
    │
    └── delete or irreversibly remove information
```

These are different operations.

## 4.8 Present-First Principle

Node Core OS adopts the following conceptual principle:

> **The present is the default context. The past is available as evidence, but it is not automatically applied. A current requirement determines whether historical context should be remembered.**

Formally:

```text
Present
   │
   ▼
Default Context
   │
   ▼
Requirement
   │
   ├── historical context unnecessary
   │        │
   │        ▼
   │     continue
   │
   └── historical context necessary
            │
            ▼
         REMEMBER
            │
            ▼
     Relevant Evidence
            │
            ▼
      Current Evaluation
```

This principle allows Node Core OS to preserve continuity without making historical information an unavoidable permanent context.

## 4.9 Requirement-Driven Memory

The resulting model can be summarized as:

```text
REQUIREMENT
     │
     ▼
MEMORY REQUIREMENT
     │
     ▼
SELECTIVE RECALL
     │
     ▼
RELEVANT EVIDENCE
     │
     ▼
CURRENT DECISION
```

Not:

```text
HISTORY
   │
   ▼
PERMANENT IDENTITY
   │
   ▼
AUTOMATIC TRUST
```

This distinction is particularly important for systems involving identity, reputation, authorization, governance, distributed participation, credentials, and privacy.

## 4.10 Core Principle

> **Node Core OS does not need to erase the past in order to forget it. It can preserve historical memory while choosing not to apply that memory to the present until a current requirement explicitly makes the relevant history necessary.**

Or, more concisely:

```text
FORGET
=
Do not apply the past by default.

REMEMBER
=
Apply only the relevant past when the present requires it.
```

This establishes **requirement-driven memory** as a fundamental architectural capability of Node Core OS.

---
# 6. Records

Records are a fundamental component of a person's digital continuity.

A record should not be treated merely as a file.

Conceptually, a record may contain:

```text
RECORD
├── Associated Identity
├── Intention
├── Purpose
├── Context
├── Importance
├── Time
├── Duration
├── Provenance
├── Integrity
├── Relationships
├── Evidence
├── Corroborations
└── Storage Policy
```

Not every record needs the same lifetime.

A record may be:

- temporary;
- ephemeral;
- persistent;
- historical;
- archived;
- canonical;
- derived.

The architecture should allow the person to determine which records should remain and which should not.

---

# 6. Local and Decentralized Storage

Storage is the first infrastructure layer of Node Core OS.

```text
                    NODE CORE OS
                         │
                    Storage Layer
                         │
                ┌────────┴────────┐
                ▼                 ▼
          Local Storage       Kubo / IPFS
```

## Local Storage

Local storage can preserve:

- files;
- configurations;
- keys;
- records;
- databases;
- states;
- temporary data;
- private information.

## Kubo / IPFS

Kubo provides the IPFS implementation used by Node Core OS.

It enables operations involving:

- content-addressed data and CIDs;
- distributed storage;
- content retrieval;
- pinning;
- publishing;
- exchange between Nodes.

Kubo is an infrastructure component used by Node Core OS. It is **not the complete definition of Node Core OS**.

---

# 7. Content and Evidence

A file can become a content reference independent of its original local path:

```text
File
 │
 ▼
Add
 │
 ▼
IPFS
 │
 ▼
CID
 │
 ├── Pin
 ├── Retrieve
 ├── Publish
 └── Share
```

This allows evidence to be referenced through content-addressed integrity mechanisms without depending exclusively on a local filesystem path.

Evidence may subsequently be associated with:

- an identity;
- a request;
- an event;
- an action;
- a protocol;
- a context;
- a corroboration.

---

# 8. Identity

Identity in Node Core OS should not be reduced to a username.

Identity should be capable of representing continuity across identifiers, records, credentials, and evidence associated with a person or entity.

Conceptually:

```text
INDIVIDUAL
  │
  ├── Individual Identity
  │
  ├── Personal Identity
  │
  └── Professional Identity
         │
         ├── Public Posture
         └── Private Posture
```

These identities do not necessarily represent different people.

They may represent different legitimate expressions of the same individual within different contexts.

The architecture should support relationships between:

```text
Identity
  │
  ├── Identifiers
  ├── Keys
  ├── Credentials
  ├── Records
  ├── Evidence
  └── Relationships
```

Cryptography can demonstrate control over an identifier or key.

However, cryptographic control alone does not prove that one unique physical person exists behind all identifiers.

For that reason, Node Core OS considers an additional layer of **corroboration and consistency**.

---

# 9. Individuality and Consistency

A central idea of the proposal is that the same identity should not be able to receive mutually incompatible attributions as though they all belonged to one coherent individual continuity.

Identity-related information can therefore be examined against constraints involving:

- time;
- space;
- physical feasibility;
- mathematics;
- causality;
- logic;
- context.

For example, if the same identity is recorded performing an activity that is physically incompatible with another activity attributed to that identity during the same time interval, the system should identify a contradiction that requires investigation.

```text
IDENTITY
  │
  ├── Event A
  │     │
  │     └── location / time
  │
  └── Event B
        │
        └── location / time
               │
               ▼
           CONSISTENCY
               │
        ┌──────┴──────┐
        ▼             ▼
    Compatible    Contradiction
```

This does not mean that physical laws or mathematics, by themselves, prove who a person is.

They can instead provide a **contradiction-detection and corroboration layer**.

The purpose is to prevent the system from treating an identity history as coherent when the attributed events contain impossible or mutually incompatible conditions, subject to the assumptions and trustworthiness of the underlying evidence.

---

# 10. Evidence

Evidence is the relationship between a claim and the records that can support it.

A conceptual chain is:

```text
IDENTITY
   ↓
RECORD
   ↓
EVIDENCE
   ↓
CORROBORATION
   ↓
CONSISTENCY
   ↓
HISTORY
   ↓
REPUTATION
```

The architecture should be able to answer questions such as:

- What is being claimed?
- Who recorded it?
- When was it recorded?
- What is its origin?
- What evidence exists?
- Which identity is associated with it?
- Who corroborated it?
- In what context?
- Are there contradictions?
- Is it still valid?

Reputation should not appear magically as a number.

It should be derivable from a history of evidence.

---

# 11. Reputation

Node Core OS distinguishes:

```text
IDENTITY
  │
  └── Who?

EVIDENCE
  │
  └── What can be substantiated?

REPUTATION
  │
  └── What can be inferred about a history within a context?
```

Reputation does not need to be a universal score.

It can be contextual, such as:

- personal;
- professional;
- contractual;
- service-related;
- participation-based;
- reliability-related;
- compliance-related;
- protocol-specific.

Therefore:

> **Reputation belongs to context and should be explainable through evidence.**

A reputation may be accepted by one system and not necessarily by another.

Node Core OS does not intend to become a universal judge of reputation.

---

# 12. Distributed Corroboration

A Node Core OS network may use other Nodes to corroborate information.

The intention is not:

> "The network decides who you are."

The intention is:

> **"The network helps establish what evidence exists regarding an identity and which other Nodes can corroborate it."**

Conceptually:

```text
IDENTITY
  │
  ▼
Corroboration Request
  │
  ▼
Node Network
  │
  ├── Evidence
  ├── Manifests
  ├── Signatures
  ├── CIDs
  ├── Versions
  ├── Attestations
  └── Known inconsistencies
  │
  ▼
Corroboration Result
  │
  ▼
PERSON
```

Propagation should also not be confused with publication.

The network may propagate:

- a CID;
- a hash;
- a signature;
- a manifest;
- an attestation;
- a reference;
- a proof;
- minimal metadata.

The original content may remain local or protected.

A future Node Core OS network is therefore intended to support distributed identity and reputation manifests that allow Nodes to ask, in effect:

> **"How do we know this reputation is corroborated?"**

Other Nodes may respond with independently held evidence, attestations, references, or records showing why a claim can or cannot be corroborated.

This is distributed corroboration, not necessarily centralized identity governance.

---

# 13. Privacy

Decentralization does not mean that everything should be public.

Node Core OS must preserve a distinction between:

```text
PRESERVE
   ≠
PROPAGATE
   ≠
PUBLISH
   ≠
AUTHORIZE
   ≠
USE
```

A person may preserve evidence locally and, when necessary, present only a sufficient proof, reference, or attestation for a specific purpose.

This makes it possible to design distributed systems that can corroborate claims without requiring the complete exposure of personal information.

Privacy is therefore treated as an architectural property rather than merely an application setting.

---

# 14. Individual Decision

The goal is not to force a person to build a reputation or participate in external systems.

The goal is to allow the infrastructure to be ready when participation becomes necessary or desirable.

A person may eventually need to:

- prove who they are;
- prove that they performed an activity;
- demonstrate experience;
- demonstrate a contractual relationship;
- demonstrate a history;
- satisfy requirements for a service;
- participate in a protocol;
- request an opportunity;
- establish trust with another person;
- demonstrate historical continuity.

Node Core OS seeks to prevent that person from having to start from zero every time.

There should be a personal place where they can preserve:

> **who I am, what I have done, what I do, and what I intend to do.**

The decision to use that information remains with the person.

---

# 15. Architecture

The architecture is organized around three visible levels:

```text
Node Core OS
│
├── Node Core BIOS
├── Node Core
└── Applications
```

## Node Core BIOS

BIOS manages the infrastructure:

- Storage;
- Kubo/IPFS;
- Network;
- Services;
- Configuration;
- Security;
- Diagnostics;
- Updates;
- Lifecycle.

> **BIOS configures the Node.**

## Node Core

Node Core provides operational capabilities:

- Storage;
- Files;
- IPFS;
- CID;
- Publish;
- Retrieve;
- Pin;
- Unpin;
- Share;
- Identity;
- Evidence;
- Reputation;
- Protocols;
- Services;
- Utilities.

> **Node Core operates the Node.**

## Applications

Applications consume Node Core capabilities.

```text
Applications
      │
      ▼
Protocols
      │
      ▼
Node Core
      │
      ▼
Node Core Runtime
      │
      ├── Local Storage
      ├── Kubo / IPFS
      ├── Network
      └── Services
```

A Node installation should be able to exist without applications.

---

# 16. Protocol and Application Layer

Node Core OS is intended to provide infrastructure on which other projects can build.

An application may request Node capabilities without directly managing every internal implementation detail.

```text
Node Core OS
      │
      ▼
Node Core
      │
      ├── Storage
      ├── Identity
      ├── Evidence
      ├── Reputation
      ├── Network
      └── Services
              │
              ▼
          Protocols
              │
              ▼
         Applications
```

This allows different protocols and applications to share a common personal infrastructure.

The long-term goal is for **other systems to be able to integrate Node Core OS wherever they need it**, rather than requiring a person to migrate their entire personal infrastructure into every application.

In other words:

> **If the mountain will not go to Muhammad, the mountain comes to Muhammad.**

Node Core OS aims to make personal infrastructure portable enough to reach the systems that need it, while allowing those systems to use Node capabilities without taking ownership of the personal core.

---

# 17. Architecture Principles

## 1. The person is the center

The infrastructure exists to preserve the person's agency and decision-making capacity.

## 2. The Node is infrastructure

The Node should be useful before applications are installed.

## 3. Requests are fundamental

Operations that represent the person's intent should originate from explicit requests or defined authorizations.

## 4. Local and decentralized storage are complementary

Local storage and Kubo/IPFS serve different purposes and can coexist.

## 5. Recording does not mean publishing

Evidence can be preserved without being automatically propagated.

## 6. Identity is not reputation

Identity represents continuity and identification; reputation is derived from contextual evidence and history.

## 7. Reputation should be explainable

Meaningful reputation should be traceable to evidence and corroboration.

## 8. Consistency matters

Temporal, spatial, physical, mathematical, causal, or logical contradictions can help detect incompatible attributions.

## 9. The network corroborates; it does not govern identity

The network can contribute evidence and corroboration without becoming a universal authority over the person.

## 10. Applications are a higher layer

Applications should use Node Core rather than replace it.

## 11. Privacy is architectural

There must be a meaningful distinction between preservation, sharing, propagation, publication, authorization, and use.

## 12. Infrastructure should be reusable

Node Core OS should be capable of becoming a foundation that other projects can integrate or implement.

## 13. The present is the default context

Historical information should not automatically define the current state of a Node.

## 14. Forgetting is not deletion

A Node may stop applying historical information without necessarily destroying the underlying record.

## 15. Memory is requirement-driven

Historical context should be recalled selectively when a current requirement requires it.

---

# 18. Complete Model

The complete conceptual model can be expressed as:

```text
                              PERSON
                                 │
                                 ▼
                         ┌───────────────┐
                         │ NODE CORE OS  │
                         └───────┬───────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
               REQUESTS                INFRASTRUCTURE
                    │                         │
                    │              ┌──────────┼──────────┐
                    │              ▼          ▼          ▼
                    │           LOCAL       KUBO       NETWORK
                    │          STORAGE      / IPFS
                    │              │          │
                    └──────────────┴──────────┘
                                 │
                                 ▼
                              RECORDS
                                 │
                                 ▼
                              EVIDENCE
                                 │
                                 ▼
                           CORROBORATION
                                 │
                                 ▼
                              PRESENT
                                 │
                                 ▼
                           REQUIREMENT
                                 │
                                 ▼
                             REMEMBER
                                 │
                                 ▼
                         RELEVANT HISTORY
                                 │
                                 ▼
                            REPUTATION
                                 │
                                 ▼
                              PROTOCOLS
                                 │
                                 ▼
                            APPLICATIONS
                                 │
                                 ▼
                         PERSON'S DECISION
```

---

# 19. Final Goal of Node Core OS

The final goal of Node Core OS is to build infrastructure that gives a person a **personal digital core**, based on local and decentralized storage, from which they can preserve and manage their records, identity, evidence, history, and reputation.

That core should allow the person to:

- build digital continuity;
- preserve evidence of their own history;
- corroborate information when necessary;
- demonstrate specific facts without necessarily exposing all personal information;
- maintain contextual identities without losing the relationship to their individual continuity;
- detect contradictions in information attributed to an identity;
- participate in distributed networks without automatically surrendering control of personal information;
- decide when to use identity or reputation;
- respond to requirements from people, organizations, services, territories, or protocols;
- maintain personal infrastructure even as the applications they use change.

The goal is not to create a mandatory identity.

The goal is not to create a universal reputation.

The goal is not to create a network that judges people.

The goal is to create **the infrastructure that allows a person to decide whether to participate in what the world requires or offers, while carrying the information and evidence necessary to do so.**

---

# 20. Export and Interoperability Goal

Once the core infrastructure is consolidated, Node Core OS should be capable of becoming a reusable architecture or standard for other projects.

The intended direction is:

```text
OTHER PROJECT
      │
      ▼
Integrates / Implements
      │
      ▼
NODE CORE OS
      │
      ├── Storage
      ├── Identity
      ├── Evidence
      ├── Reputation
      ├── Protocols
      └── Services
      │
      ▼
APPLICATION / PROTOCOL
```

This would prevent Node Core OS from becoming an isolated system.

The long-term objective is a **portable personal infrastructure layer** that can be implemented where it is needed and can host or integrate applications and protocols where the person needs them.

The desired relationship is therefore bidirectional:

- external projects can implement or integrate Node Core OS;
- Node Core OS can provide the infrastructure required by external applications and protocols.

---

# 21. Official Platform

**Node Core OS is a GNU/Linux, terminal-first project.**

The official target is:

```text
GNU/Linux
   │
   ▼
Terminal
   │
   ▼
Node Core OS
```

The project does not currently define a graphical desktop application, mobile application, web application, Windows implementation, or macOS implementation as its official target.

The system is designed to operate without root privileges and without requiring a global system installation.

This constraint is intentional: the Node should belong to and operate within the user's own environment.

---

# 22. Installation and Dependency Contract

Node Core OS is installed and operated from a GNU/Linux terminal.

The installer is designed around the following principles:

- no root required;
- no sudo required;
- no systemd dependency;
- user-owned paths;
- user-space installation;
- isolated Kubo/IPFS configuration;
- dependency verification;
- explicit installation validation;
- no unnecessary modification of the host operating system.

The project should prefer official dependency sources and resilient fallback mechanisms. Large downloads should not be constrained by arbitrary total-transfer time limits.

Technical installation and dependency documentation is maintained in:

- `docs/DEPENDENCIES.md`;
- `docs/INSTALLER.md`;
- `installer/install.sh`.

Termux is **not an official target platform**. Constraints observed in environments such as Termux are considered only as engineering references to avoid assuming root privileges, system service managers, or protected system paths.

---

# 23. Applications and Use Cases

Node Core OS is designed as a horizontal infrastructure. Its core capabilities and trust protocols can be composed into domain-specific applications across enterprise, government, finance, education, health, logistics, industry, AI, decentralized networks, and other sectors.

The architecture is intentionally separated into three levels:

CORE INFRASTRUCTURE
        ↓
TRUST / EVIDENCE PROTOCOLS
        ↓
NC-* APPLICATIONS

Examples include:
- Enterprise: NC-SUPPLIER, NC-CONTRACT, NC-PROCUREMENT
- Finance: NC-BANK-KYC, NC-CREDIT, NC-LENDING
- Government: NC-GOV, NC-BENEFIT, NC-TAX, NC-LICENSE
- Civic: NC-ELECTOR-ID, NC-VOTING-PARTICIPATION
- Education: NC-CREDENTIAL, NC-UNIVERSITY, NC-TRAINING
- Health: NC-HEALTH, NC-MEDICAL-CREDENTIAL
- Logistics: NC-SUPPLY-CHAIN, NC-LOGISTICS, NC-CARGO
- Pharmaceutical / Food: NC-PHARMA, NC-FOOD, NC-COLD-CHAIN
- Agriculture: NC-AGRI
- Energy / Utilities: NC-ENERGY, NC-WATER, NC-GRID
- Industrial / IoT: NC-MANUFACTURING, NC-IOT, NC-ROBOTICS, NC-DIGITAL-TWIN
- Software / Provenance: NC-SOFTWARE-SUPPLY-CHAIN, NC-DOCUMENT, NC-CONTENT-PROVENANCE
- AI: NC-AI, NC-AI-AGENT, NC-MODEL-PROVENANCE
- Legal / Compliance: NC-LEGAL, NC-COMPLIANCE, NC-AUDIT
- Decentralized systems: NC-P2P, NC-CONSORTIUM, NC-DAO
- Research / Creative: NC-RESEARCH, NC-DATA-PROVENANCE, NC-CREATOR, NC-IP

These names describe proposed reference applications unless a separate document identifies a higher implementation status.

### Common application model

REQUEST → REQUIREMENT → POLICY → CURRENT CONTEXT → REMEMBER only if required → MINIMUM NECESSARY EVIDENCE → CORROBORATION / SOURCE DIVERSITY → TEMPORAL CHECKS → PROOF → DECISION → MINIMUM CONTEXT RELEASE → FORGOTTEN

The central memory principle is:

> **The present is the default context. The past remains available as evidence, but it is not automatically applied. A current requirement determines whether relevant historical context should be remembered.**

FORGOTTEN ≠ DELETED
PRESERVED ≠ ACTIVELY USED
STORE ≠ REMEMBER ≠ USE ≠ SHARE ≠ PUBLISH

The complete cross-sector catalog, protocol composition model, application template, architectural limits, and implementation-status model are maintained in docs/USE-CASES.md.

---
# 23. Project Status

Node Core OS is under active development.

This README deliberately distinguishes between:

- **Implemented** — functionality currently available;
- **In development** — functionality currently being implemented;
- **Architectural goal** — a designed capability that has not yet been fully materialized;
- **Future** — an extension that depends on previous architectural layers.

The initial foundation is:

```text
Installation
   ↓
Boot
   ↓
Node Core OS
   ↓
BIOS
   ↓
Local Storage
   ↓
Kubo / IPFS
   ↓
Node Core
   ↓
Add → CID → Pin → Retrieve
```

The architecture is then intended to progress toward:

```text
Records
   ↓
Identity
   ↓
Evidence
   ↓
Corroboration
   ↓
Reputation
   ↓
Protocols
   ↓
Applications
   ↓
Interoperability
```

The architecture described in this document represents the **long-term design direction** and does not imply that every described component is currently implemented.

---

# 24. Conceptual Roadmap

## Phase 1 — Node Infrastructure

- rootless installation;
- runtime;
- configuration;
- local storage;
- Kubo/IPFS;
- service lifecycle;
- networking;
- diagnostics.

## Phase 2 — Node Core

- storage abstraction;
- files;
- CID;
- Add;
- Retrieve;
- Pin / Unpin;
- Publish;
- Share;
- utilities.

## Phase 3 — Requests and Records

- Request model;
- records;
- intention;
- purpose;
- context;
- duration;
- storage policies;
- access control.

## Phase 4 — Identity

- Node identity;
- individual identity;
- personal identity;
- professional identity;
- public and private postures;
- identifiers;
- keys;
- credentials;
- linked records.

## Phase 5 — Evidence and Corroboration

- evidence model;
- provenance;
- attestations;
- corroboration;
- temporal consistency;
- spatial consistency;
- causal consistency;
- logical and mathematical consistency;
- contradiction detection.

## Phase 6 — Reputation

- history;
- contextual reputation;
- trust relationships;
- evidence-derived reputation;
- verification;
- reputation explanations.

## Phase 7 — Node Network

- propagation;
- discovery;
- Node-to-Node corroboration;
- manifests;
- references;
- proofs;
- synchronization;
- distributed trust mechanisms.

## Phase 8 — Protocols

- protocol model;
- lifecycle;
- services;
- Node-to-Node communication;
- distributed coordination;
- protocol-specific identity and reputation.

## Phase 9 — Applications

- installation;
- permissions;
- storage;
- identity;
- requests;
- services;
- networking;
- lifecycle.

## Phase 10 — Standardization and Interoperability

- APIs;
- schemas;
- export formats;
- integration mechanisms;
- embedding Node Core OS into other projects;
- implementing applications and protocols on top of Node Core OS.

---

# 25. Final Principle

Node Core OS can be summarized as:

```text
PERSON
   ↓
REQUEST
   ↓
NODE CORE OS
   ↓
RECORD
   ↓
EVIDENCE
   ↓
CORROBORATION
   ↓
IDENTITY / HISTORY / REPUTATION
   ↓
PROTOCOL
   ↓
APPLICATION
   ↓
PERSON'S DECISION
```

The Node does not decide who a person must be.

It does not decide what reputation a person must have.

It does not decide what a person must publish.

It does not decide what a person must participate in.

**It provides the infrastructure through which a person can make those decisions with information, evidence, continuity, and the ability to seek corroboration.**

That is the long-term purpose of **Node Core OS**.

---

# Project

**Node Core OS**  
byLAEV

Repository: https://github.com/byLAEV/Node-Core-OS/
