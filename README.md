> “I am mentally retarded, but not so mentally retarded that I don't know how to make the original the original and the copy the copy.”

# Node Core OS byLAEV

**Personal digital infrastructure for local storage, decentralized content, identity, evidence, and reusable protocols.**

Node Core OS is an infrastructure project designed to give people and entities a digital core from which to manage resources, records, identity-related data, and applications. It combines local storage with integration for Kubo/IPFS and provides a foundation on which additional protocols and applications can be developed.

- **Repository:** https://github.com/byLAEV/Node-Core-OS/
- **Version recorded in `VERSION`:** 1.5.4
- **Primary environment:** GNU/Linux terminal
- **Project status:** Active development; individual capabilities have different implementation and verification states.

> **Implementation status matters:** architectural goals and proposals in this README are not claims that every described protocol, public API, or distributed feature is already implemented or production-ready.

## 1. Project idea

Node Core OS is intended to be more than a file-storage application. It is a personal digital infrastructure that can support records, content, identity, evidence, corroboration, and eventually a broader ecosystem of protocols and applications.

The core relationship is:

```text
PERSON OR ENTITY
       |
       v
  NODE CORE OS
       |
       +-- Local storage
       +-- Kubo / IPFS integration
       +-- Content registry
       +-- Technical node identity
       +-- Personal and institutional identity models
       +-- Protocols and evidence
       +-- Applications and integrations
```

The infrastructure should exist independently of any single application. Applications should use explicit, documented capabilities rather than duplicating the core or relying on undocumented internal details.

## 2. Design principles

- **User control:** users should be able to understand and control what is recorded, retained, verified, used, or shared.
- **Transparency:** operations, data formats, errors, and limitations should be documented and testable.
- **Local-first foundations:** local storage and decentralized storage are separate domains with explicit behavior.
- **Explicit publication:** storing information locally must not silently publish it or authorize its propagation.
- **Identity clarity:** user-declared information, cryptographic control, third-party verification, evidence, and decisions are different concepts.
- **Least privilege:** applications and nodes should receive only the access required for a defined operation.
- **Interoperability:** public interfaces should have stable, versioned contracts and documented compatibility.
- **Testable implementation:** features should be described as implemented or verified only when code and appropriate tests support that claim.
- **Incremental security:** security mechanisms should follow a clear threat model and functional requirements. Advanced cryptographic techniques, including zero-knowledge proofs, must be used only where their guarantees are understood and relevant.

## 3. Architecture

At a high level, Node Core OS is organized around infrastructure, runtime and BIOS-level administration, storage, content management, identity, protocols, and applications.

### Node Core BIOS and services

The BIOS layer provides an administrative boundary for node configuration and core services. The architecture documentation describes service management and the separation between Node Core storage and Kubo's own repository.

Kubo is an external infrastructure dependency; Node Core OS does not reimplement IPFS and should not expose Kubo's administrative RPC as a substitute for a documented application API.

See [Implementation Architecture](docs/ARCHITECTURE.md).

### Local storage

Local storage is used for resources and application data managed by the Node Core OS installation. The installed data directory is normally under `~/.node-core/`, with separate areas for application code, configuration, storage, logs, runtime files, and IPFS data.

### Kubo / IPFS content

The content layer works with content identifiers (CIDs) and Kubo/IPFS operations. The architecture documentation describes a content path that includes adding content, registering metadata, retrieving content, pinning or unpinning, publishing, and sharing references.

A CID identifies content; it does not by itself identify its author, prove a claim about that author, guarantee permanent network availability, or grant access permissions.

Pinning asks a particular Kubo node to retain content. Unpinning or deleting a local copy does not guarantee that other network participants have removed their copies.

Publishing is a distinct operation. Users should consider privacy before publishing personal or confidential information.

See [Implementation Architecture](docs/ARCHITECTURE.md) and [My Life / Node Blog](docs/MY-LIFE-BLOG.md).

## 4. Identity: technical node identity and human identity

Node Core OS distinguishes a technical node identity from personal or institutional identity information.

### Technical node identity

The current technical identity implementation uses Ed25519 keys and creates a persistent node identifier with a `sha256:` prefix. The identity store includes code and tests for initialization, persistence, and handling an incomplete identity.

A cryptographic node identity can support operations that depend on control of a key. It does **not** independently establish a person's civil identity, uniqueness, legal status, or trustworthiness.

The implementation documentation also notes that the private key is stored as a PEM file protected by filesystem permissions. Those permissions are a baseline safeguard, not protection against every threat, including a compromised process running as the same user.

### Personal and institutional identity

The broader design aims to support personal, professional, business, legal, institutional, and governmental identity use cases. Identity information may be declared by a user or supported by evidence from an identified issuer or verification procedure.

A locally entered profile is a declaration, not proof that the person holds a document or that the document is valid. Any future verification process should state who or what performed the check, what evidence was checked, the scope of the result, and when it occurred.

### SHA-256 and the Identity API

The project's design direction includes SHA-256 as a stable root identifier. A public identity contract must specify exactly what bytes or canonical representation are hashed, how versions and normalization are handled, and how the identifier relates to keys, credentials, and identity records.

SHA-256 alone does not authenticate a person, prove human uniqueness, or replace digital signatures and issuer verification.

**API status:** the repository's [API Contract](docs/API-CONTRACT.md) is explicitly a proposed contract, not a claim that a stable public API is implemented. The [SDK Integration Guide](docs/SDK-INTEGRATION.md) is a guide and roadmap, not evidence of a released official SDK.

## 5. Identity Tools and Node Services byLAEV

For the detailed certificate and node-identity security report, including architecture, test scope, reproducible commands, CI evidence, limitations, and pending work, see the [Official Node Identity Certificates Security Report (English)](docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.en.md). The [Spanish version](docs/IDENTITY-NODE-CERTIFICATES-SECURITY-REPORT.md) is also available.

The identity-related tools are a **product and service layer within Node Core OS**, not a separate operating system and not a claim that every proposed service is already available. Their purpose is to let personal identities and their authorized nodes perform useful, verifiable work: manage credentials, verify signed claims, protect node-to-node interactions, produce evidence, and—once a real service and payment system exist—receive compensation for accepted work.

The dedicated `tools/` directory is the catalog and design area for these tools. It keeps product definitions, scope, requirements, and acceptance criteria separate from the reusable Node Core runtime. Implementations should be integrated into the core only through documented interfaces, explicit authorization, and tests.

### Product families

- **Identity and device credentials (CMI / SCC):** a proposed lifecycle for personal identity anchors and subordinate device credentials, including issuance, verification, expiry, renewal, delegation, and revocation. A signature can authenticate a credential's issuer and integrity; it does not independently prove that a real-world identity claim is true or unique.
- **Node trust and security services:** planned verification of credentials and signed events, revocation status, access control, abuse controls, and auditable service results. A valid credential does not, by itself, prevent denial-of-service attacks or authorize every action.
- **Portable attestations and reputation evidence:** a planned way to carry signed, contextual attestations and evidence between services. Reputation is not a universal score; claims should be attributable, scoped, reviewable, and correctable.
- **Operator tools and service marketplace:** a future layer through which node operators, identity holders, developers, and service providers can perform requested work and be paid for measurable, accepted service. Node uptime or registration alone does not guarantee compensation.

### Participation and compensation model

Node Core OS is intended to let people and their nodes participate in useful services—not to sell a person's identity. Potential paid work may include credential verification, authorized attestations, availability, data distribution, auditing, or other explicitly defined tasks. Each paid task needs a service specification, acceptance criteria, evidence of completion, a disclosed price or reward rule, and a dispute path.

Payments are **a product direction, not an existing earning guarantee**. No participant should be promised income merely for registering an identity, running a node, purchasing equipment, recruiting others, or holding a token. Revenue must come from customers paying for useful services, and the distribution model must account for operating costs, payment fees, taxes, legal obligations, fraud, and disputes.

### Scope and implementation boundaries

The tools must preserve the distinction between:

1. a person's declared identity information;
2. cryptographic proof of control of a key;
3. an issuer's claim and its verification evidence;
4. authorization to perform a specific action;
5. evidence that a service task was completed; and
6. the business rule used to calculate and distribute payment.

Multiple nodes operated by one person must not automatically multiply that person's human vote or identity uniqueness. Technical node consensus and human governance are separate mechanisms and require their own rules.

The first implementation stage prioritizes transparent data structures, reproducible cryptographic verification, explicit consent, key lifecycle, expiry and revocation, access control, tests, and auditable service records. Privacy enhancements—including selective disclosure and zero-knowledge proofs—may follow when the requirements and guarantees are defined. The tools must not collect or publish sensitive personal data by default.

**Current status:** the `tools/` catalog documents product direction and proposed contracts. It does not assert that CMI/SCC issuance, production PKI, global identity uniqueness, a reputation network, a service marketplace, or participant payments are complete or production-ready. Each capability must earn its status through implementation, tests, security review, and documented operational evidence.

See [Identity Tools catalog](tools/README.md) for product boundaries, planned components, and staged acceptance criteria.

## 6. Node networking, corroboration, and consensus

The long-term architecture contemplates multiple nodes exchanging references, records, and evidence through explicit protocols. These capabilities must be treated as distinct concerns:

- Node identification.
- Authentication of communications.
- Authorization between nodes.
- Peer discovery.
- Data exchange and synchronization.
- Corroboration of records.
- Agreement on a defined state or evidence set.

A network connection does not by itself make a peer trustworthy. Likewise, a collection of signatures is not automatically a valid consensus. Each protocol needs a defined purpose, trust model, failure behavior, and testable acceptance criteria.

Consensus-related work is intended to make states and supporting evidence comparable across nodes, including references to external repository states. The exact scope and implementation status of each consensus feature must be established by its code, tests, and documentation. Global peer discovery or production-grade distributed consensus should not be inferred from the existence of architectural plans.

## 7. Records and My Life / Node Blog

My Life / Node Blog is documented as a local-first personal record feature. Entries are stored as Markdown files under the local Node Core data directory, with metadata maintained in a local index.

The documented interface supports paginated browsing, search, and opening an individual entry. Publishing an entry to IPFS is a separate, explicit action. The feature does not imply that every local entry is published automatically.

A published CID can be associated with an entry, and the user can choose whether the local Kubo node pins the content. Publication and pinning have privacy and availability implications.

See [My Life / Node Blog documentation](docs/MY-LIFE-BLOG.md).

## 8. Remembering, forgetting, and data lifecycle

The proposed future architecture separates historical retention from applying historical information to a current request.

```text
CURRENT REQUEST
      |
      v
PURPOSE AND REQUIREMENT
      |
      v
IS HISTORICAL CONTEXT NEEDED?
      |
      +-- NO --> Do not apply history by default
      |
      +-- YES -> Retrieve the minimum relevant evidence
```

The design distinguishes several operations:

- **Preserve:** retain a record.
- **Remember:** retrieve and apply historical context for a particular purpose.
- **Restrict:** prevent specified access or use.
- **Expire:** mark a record or credential beyond its validity boundary.
- **Revoke:** invalidate a credential or authorization under its governing policy.
- **Delete or purge:** remove data from storage locations controlled by the system, subject to the defined policy.
- **Unpin:** stop requesting local Kubo persistence for a CID.
- **Publish or share:** make content or a reference available to others.

These operations are not interchangeable. In particular, forgetting from an active context is not the same as deleting a record, and unpinning is not proof of network-wide deletion.

**Status:** [Remembering & Forgetting](docs/REMEMBERING-FORGETTING.md) is a proposed future architecture, not a claim that a complete selective-memory system is implemented.

## 9. Public APIs and third-party applications

Node Core OS aims to expose documented interfaces through which external applications can request supported core capabilities.

A public API should define inputs, outputs, structured errors, authorization requirements, version compatibility, and tests. Integrating an application must not grant unrestricted access to private files, identity records, credentials, keys, or administrative services.

The expected integration pattern is:

```text
EXTERNAL APPLICATION
        |
        v
VERSIONED PUBLIC API
        |
        v
VALIDATION AND AUTHORIZATION
        |
        v
NODE CORE OS CAPABILITY
        |
        v
DOCUMENTED RESULT
```

Do not treat proposed endpoints or SDKs as available until they are implemented, tested, and documented as supported.

- [API Contract](docs/API-CONTRACT.md)
- [SDK Integration Guide](docs/SDK-INTEGRATION.md)

## 10. Installation

### GNU/Linux

The documented primary platform is a GNU/Linux terminal environment. The installer is designed to run as the normal user and refuses root execution.

Requirements include GNU/Linux, Bash, Python 3.10 or later, standard terminal utilities, and the required download and verification tools. Kubo is required for IPFS-dependent features. See [Dependencies](docs/DEPENDENCIES.md) for the full contract.

From a local checkout of the repository:

```bash
git clone https://github.com/byLAEV/Node-Core-OS.git
cd Node-Core-OS
bash installer/install.sh
```

Run the installer as your normal user, without `sudo`. The installer checks the platform and dependencies, prepares the user-owned data directory, installs the application and required runtime components, verifies the installation, and prints first-start instructions.

If an installation already exists, use its documented updater rather than running a fresh installation over existing data.

See [Installer Specification](docs/INSTALLER.md).

### Termux on Android

The repository also contains a Termux-specific installer entry point for Android ARM64:

```bash
bash installer/termux-install.sh
```

This command is intended to be run from the appropriate Termux environment, not from a generic GNU/Linux shell. It checks the Termux environment and installs missing Termux packages before invoking the main installer.

The repository's platform documents have not always described Termux consistently. Check [Termux documentation](docs/TERMUX.md) and [Dependencies](docs/DEPENDENCIES.md) for current restrictions and release-specific prerequisites before relying on a published package. Do not assume a release archive contains a wrapper added after that release was built.

Windows and macOS are not documented as supported targets.

## 11. Implementation status and roadmap

Node Core OS includes executable infrastructure alongside proposals and future architecture. A document or catalog entry is not, by itself, evidence that a feature is implemented, tested, audited, or deployed.

Use these meanings when describing project status:

| Status | Meaning |
| --- | --- |
| **Implemented** | Relevant code exists. |
| **Verified** | Defined tests passed in the stated environment. |
| **In development** | Implementation work remains in progress. |
| **Proposed** | A design or contract exists, but the capability is not implemented as a complete supported feature. |
| **Future** | The capability depends on later work or architectural decisions. |

The project's broad development directions include:

1. Maintain the node runtime, installer, and lifecycle.
2. Improve local storage and Kubo/IPFS content management.
3. Maintain persistent technical node identity.
4. Define personal and institutional identity contracts.
5. Implement and test public API contracts.
6. Establish authorized node-to-node communication and discovery.
7. Develop evidence, provenance, corroboration, and consensus protocols.
8. Build reusable domain applications on top of tested core capabilities.
9. Evaluate advanced cryptographic mechanisms where requirements justify them.

This list describes development direction, not a statement that every item is complete.

## 12. Development and contribution principles

Contributions should favor explicit, understandable, reproducible, and testable implementation.

- Inspect existing code and contracts before adding a new interface.
- Preserve user data and compatibility with existing installations.
- Test successful operations, invalid inputs, authorization failures, and relevant backend failures.
- Document whether an operation changes local data, publishes content, or affects a distributed reference.
- Never claim verification without supporting test results.
- Keep public contracts separate from internal implementation details.
- Avoid unnecessary dependencies and hard-coded secrets.
- Document known limitations and supported environments.

Before proposing a new protocol, define its purpose, participants, inputs, outputs, trust assumptions, failure cases, and acceptance tests.

## 13. Documentation

| Document | Purpose |
| --- | --- |
| [Implementation Architecture](docs/ARCHITECTURE.md) | Core components and implementation boundaries. |
| [Dependencies](docs/DEPENDENCIES.md) | Platform and runtime requirements. |
| [Installer Specification](docs/INSTALLER.md) | Installation and update behavior. |
| [Termux Guide](docs/TERMUX.md) | Android Termux installation path. |
| [API Contract](docs/API-CONTRACT.md) | Proposed public API contract. |
| [SDK Integration](docs/SDK-INTEGRATION.md) | Integration requirements and roadmap. |
| [Identity Design Principles](docs/IDENTITY-DESIGN-PRINCIPLES.md) | Identity, declarations, and verification boundaries. |\n| [Identity Tools catalog](tools/README.md) | Product scope, service families, implementation boundaries, and acceptance stages. |
| [Remembering & Forgetting](docs/REMEMBERING-FORGETTING.md) | Proposed contextual-history architecture. |
| [Use Cases](docs/USE-CASES.md) | Protocol and application catalog. |
| [My Life / Node Blog](docs/MY-LIFE-BLOG.md) | Personal records and IPFS publication behavior. |

## 14. License and repository information

Check the repository's [LICENSE](LICENSE) file for the terms that apply to this project, and review the repository for contribution guidance before submitting changes.

- **Repository:** https://github.com/byLAEV/Node-Core-OS/
- **Issues and development:** use the repository's GitHub issue and pull request workflows.

## 15. Long-term vision

Node Core OS byLAEV aims to provide reusable digital infrastructure on which people, organizations, and applications can manage resources, identity-related information, and evidence through explicit protocols.

The core should provide shared capabilities so that applications do not each need to recreate their own storage, identity, and resource-management systems. The long-term direction is an interoperable, distributed, and decentralized ecosystem that maintains clear distinctions between data, evidence, identity, authorization, and decisions.

**Node Core OS provides the infrastructure. Protocols define reusable rules. Applications compose those capabilities for specific purposes. Code and tests determine which capabilities are actually available.**
