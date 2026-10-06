# Node Core OS

**Node Core OS** is a node infrastructure designed to manage local and decentralized resources as a unified environment for running protocols, services, and applications in a distributed and decentralized manner.

The project is built around a simple architectural principle:

> **The Node is the infrastructure. Node Core is the interface to that infrastructure. Applications are built on top of it.**

Node Core OS is designed around two complementary storage environments:

- **Local Storage** — resources stored directly on the Node.
- **Kubo / IPFS** — decentralized, content-addressed storage and retrieval.

The purpose of Node Core OS is not to make these environments compete. It is to provide a common Node-level architecture through which storage, networking, services, identity, reputation, protocols, and applications can progressively operate over the same Node.

---

# Architecture

Node Core OS has three visible architectural levels:

```text
Node Core OS
│
├── Node Core BIOS
├── Node Core
└── Applications
```

These levels have distinct responsibilities.

```text
                         Node Core OS
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
          BIOS            Node Core       Applications
             │                │                │
      administration      operation         programs
             │                │                │
             └────────────────┼────────────────┘
                              │
                       Node Core Runtime
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
           Storage          Network         Services
              │
        ┌─────┴─────┐
        ▼           ▼
      Local       Kubo/IPFS
     Storage
```

The three visible levels are deliberately separated from the underlying runtime.

---

# Node Core BIOS

**Node Core BIOS is the administrative layer of the Node.**

It is inspired by the role of a BIOS: it is the place where the fundamental configuration, state, services, and lifecycle of the Node are managed before higher-level use.

BIOS answers:

> **How does this Node exist and operate?**

The intended administrative architecture is:

```text
Node Core BIOS
│
├── Storage
├── IPFS / Kubo
├── Network
├── Services
├── Configuration
├── Security
├── Diagnostics
├── Updates
└── Lifecycle
```

BIOS responsibilities can include:

- configuring local storage
- managing storage locations and state
- installing and configuring Kubo
- starting and stopping Kubo
- inspecting IPFS status
- managing Node services
- managing network configuration
- maintaining Node configuration
- diagnostics and health checks
- security configuration
- updates
- Node lifecycle operations

> **BIOS configures the Node.**

The initial implementation can begin with Storage and IPFS / Kubo while preserving the complete administrative boundary for future development.

---

# Node Core

**Node Core is the operational layer of the Node.**

Node Core answers:

> **What can I do with this Node?**

The intended operational surface includes:

```text
Node Core
│
├── Storage
├── IPFS
├── Files
├── CID
├── Publish
├── Retrieve
├── Pin
├── Unpin
├── Share
└── Utilities
```

Node Core provides abstractions over the infrastructure so that protocols and applications do not need to directly manage every low-level detail of local storage, Kubo, services, or other Node resources.

> **BIOS configures the Node.**  
> **Node Core uses the Node.**

---

# Applications

Applications are the third architectural level.

They are intentionally separated from Node Core.

```text
Applications
│
├── App 001
├── App 002
├── App 003
└── ...
```

A new installation does not require applications.

The initial state can therefore be:

```text
Applications

No applications installed.

[Future]
```

This establishes a clear boundary:

- **BIOS** manages infrastructure.
- **Node Core** provides infrastructure capabilities.
- **Applications** consume those capabilities.

Applications can therefore evolve independently from the fundamental Node infrastructure.

---

# Node Core Runtime

BIOS and Node Core are not two independent systems.

They operate over a common **Node Core Runtime**.

```text
                    Node Core OS
                         │
                        boot
                         │
                         ▼
                  Node Core Runtime
                         │
              ┌──────────┴──────────┐
              │                     │
             BIOS                  Core
              │                     │
              └──────────┬──────────┘
                         │
                    Node Resources
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Storage         Network        Services
          │
     ┌────┴────┐
     ▼         ▼
   Local     Kubo
  Storage    / IPFS
```

The Runtime is the common technical foundation that connects the user-facing architecture with the resources of the Node.

This prevents BIOS and Node Core from duplicating infrastructure logic and allows additional resources to be introduced later without changing the fundamental three-level model.

---

# Storage Architecture

Storage is a fundamental abstraction of Node Core OS.

```text
                 Node Core
                     │
              Storage Abstraction
                     │
             ┌───────┴───────┐
             │               │
             ▼               ▼
        Local Storage      IPFS
```

## Local Storage

Local Storage represents resources stored directly on the Node.

It can provide:

- filesystem access
- storage paths
- file management
- local capacity
- local persistence
- local state
- local retrieval

## Kubo / IPFS

Kubo provides the IPFS implementation used by Node Core OS.

IPFS introduces content-addressed storage and decentralized retrieval into the Node.

Kubo is therefore an infrastructure component of the Node rather than the definition of Node Core itself.

```text
Node Core BIOS
      │
      ▼
Kubo / IPFS
      │
      ▼
Node Core
      │
      ├── Files
      ├── CID
      ├── Pin
      ├── Retrieve
      └── Publish
```

---

# Content Model

A central Node Core flow is:

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
 ├── Publish
 └── Retrieve
```

A file can move from a local representation into a content-addressed representation.

The CID identifies the content independently from its local filesystem path.

This creates a foundation for protocols and applications that can reference and exchange content without depending exclusively on one local filesystem.

---

# Identity

Identity is a higher-level Node system built on top of the infrastructure.

The Node must eventually be able to distinguish:

- the Node itself
- identities associated with the Node
- applications operating on the Node
- protocols operating through the Node
- resources and content associated with an identity
- relationships between identities and Nodes

Identity should not be treated as merely a username.

The intended architecture is closer to:

```text
Node
 │
 ├── Node Identity
 │
 ├── Identity Records
 │
 ├── Public Keys
 │
 ├── Credentials
 │
 ├── Capabilities
 │
 └── Identity-linked Resources
```

A future identity layer can provide cryptographic references that allow other Nodes and applications to determine which identity is associated with an operation without making identity itself dependent on a centralized database.

The underlying storage and content systems remain independent from the identity layer.

---

# Reputation

Reputation is distinct from identity.

> **Identity answers who is associated with an action. Reputation describes what can be learned about the history and reliability of that identity, Node, service, or resource.**

The intended model is therefore:

```text
Identity
   │
   ▼
Activity / Evidence
   │
   ▼
Claims / Attestations
   │
   ▼
Reputation
```

Reputation should not be treated as a single universal score controlled by Node Core OS.

Instead, the architecture can support multiple sources and contexts of reputation:

```text
                 Reputation
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   Identity       Node          Service
   reputation   reputation     reputation
       │             │             │
       └─────────────┼─────────────┘
                     ▼
                  Evidence
```

Potential reputation inputs include:

- signed attestations
- completed interactions
- service history
- content provenance
- protocol participation
- reliability observations
- application-specific evaluations
- relationships with other identities
- historical evidence

This allows reputation systems to remain contextual rather than forcing every application into one centralized ranking.

---

# Identity, Reputation and Content

One of the long-term goals is to connect identity and reputation with content and actions without coupling them to the underlying storage implementation.

A possible conceptual flow is:

```text
Identity
   │
   ▼
Action
   │
   ├── Content
   │     │
   │     ▼
   │    CID
   │
   ├── Node
   │
   └── Protocol
          │
          ▼
       Evidence
          │
          ▼
      Reputation
```

For example, a published resource could eventually contain or reference:

```text
Content
│
├── CID
├── Publisher Identity
├── Timestamp / metadata
├── Provenance
├── Protocol context
└── Attestations
```

The important architectural principle is that **content, identity, and reputation remain separate primitives that can be composed**.

---

# Trust and Reputation Are Not the Same as Identity

Node Core OS should preserve this distinction:

```text
Identity
   │
   └── Who?

Trust
   │
   └── What relationship or confidence exists?

Reputation
   │
   └── What evidence exists about previous behavior?
```

An identity can therefore exist without a reputation.

A Node can have a reputation without every application accepting that reputation.

An application can establish its own trust rules without modifying the fundamental Node identity system.

This is important for decentralized systems because different protocols may legitimately evaluate the same identity differently.

---

# Protocol Layer

Node Core OS is intended to become infrastructure for protocols, not only file operations.

The long-term relationship is:

```text
Node Core OS
      │
      ▼
Node Runtime
      │
      ▼
Node Core
      │
      ├── Storage
      ├── Network
      ├── Services
      ├── Identity
      ├── Content
      └── Capabilities
              │
              ▼
          Protocols
              │
       ┌──────┼──────┐
       ▼      ▼      ▼
    Protocol Protocol Protocol
       │      │      │
       └──────┼──────┘
              ▼
        Applications
```

A protocol should be able to consume Node Core capabilities without needing to know every implementation detail of the underlying Node.

This creates a separation between:

- infrastructure
- protocol logic
- application logic

---

# Services

Services are persistent or managed processes that operate on the Node.

They belong conceptually to the infrastructure layer and are therefore managed by BIOS and exposed through Node Core when appropriate.

Examples may eventually include:

- Kubo
- network services
- indexing services
- identity services
- protocol services
- application services
- synchronization services
- discovery services

The service lifecycle is intended to follow:

```text
Install
   │
   ▼
Configure
   │
   ▼
Enable
   │
   ▼
Start
   │
   ▼
Running
   │
   ├── Status
   ├── Diagnostics
   ├── Restart
   └── Stop
```

---

# Network Architecture

Network management belongs to BIOS because the network is part of the Node infrastructure.

Node Core can then expose higher-level network capabilities to protocols and applications.

```text
BIOS
 │
 └── Network configuration
          │
          ▼
     Node Runtime
          │
          ▼
      Node Core
          │
     ┌────┴────┐
     ▼         ▼
 Protocols  Applications
```

The architecture is intended to support both local and decentralized communication without requiring every application to implement its own Node management.

---

# Security

Security is an infrastructure concern.

The intended security architecture can eventually cover:

- Node configuration
- local permissions
- service permissions
- application permissions
- identity keys
- credential storage
- resource access
- protocol authorization
- capability management
- secure lifecycle operations

Security should remain layered rather than being reduced to one authentication mechanism.

```text
Node Security
│
├── Node
├── Services
├── Identity
├── Applications
├── Protocols
└── Resources
```

---

# Applications and Permissions

Applications are consumers of Node Core capabilities.

A future application model can define:

```text
Application
│
├── Identity
├── Permissions
├── Services
├── Storage
├── Protocols
└── Lifecycle
```

Applications should not automatically receive unrestricted access to the Node.

A permission/capability system can eventually determine whether an application can:

- read local files
- write local files
- access IPFS
- publish content
- retrieve content
- use network resources
- access identity capabilities
- run services
- communicate with other applications

This creates an explicit boundary between the Node and software running on it.

---

# Node Lifecycle

The complete Node lifecycle is intended to be manageable through the architecture:

```text
Install
   │
   ▼
Initialize
   │
   ▼
Configure
   │
   ▼
Boot
   │
   ▼
Node Core Runtime
   │
   ├── Storage
   ├── Network
   ├── Services
   └── Kubo / IPFS
   │
   ▼
Node Ready
   │
   ├── BIOS
   ├── Node Core
   └── Applications
   │
   ▼
Operate
   │
   ├── Maintain
   ├── Update
   ├── Backup
   └── Shutdown
```

The lifecycle is deliberately separated from application lifecycle.

---

# User Interface

The initial interface is intentionally simple and menu-driven.

## Main Menu

```text
Node Core OS
byLAEV

0. Exit
1. Node Core BIOS
2. Node Core
3. Applications

>
```

## Node Core BIOS

The complete intended administrative surface is:

```text
Node Core BIOS
byLAEV

0. Back
1. Storage
2. IPFS / Kubo
3. Network
4. Services
5. Configuration
6. Security
7. Diagnostics
8. Updates
9. Lifecycle

>
```

## Node Core

The complete intended operational surface is:

```text
Node Core
byLAEV

0. Back
1. Storage
2. IPFS
3. Files
4. CID
5. Publish
6. Retrieve
7. Pin
8. Unpin
9. Share
10. Identity
11. Reputation
12. Protocols
13. Services
14. Utilities

>
```

## Applications

```text
Applications
byLAEV

No applications installed.

[Future]
```

The menu is an interface to the architecture, not the architecture itself. Internal modules should remain independent from the presentation layer.

---

# Platform Scope

**Node Core OS is strictly a GNU/Linux terminal project.**

The repository, runtime, user interface, installation model, documentation, and official CI target GNU/Linux systems operated from a terminal.

The official scope is:

```text
GNU/Linux
   │
   └── Terminal
        │
        └── Node Core OS
```

The project does not define a graphical desktop application, web application, mobile application, Windows target, or macOS target.

Portability experiments on other environments, if performed, are external validation work and do not change the official platform contract of this repository.

---

# Installation

Node Core OS is designed to be installed and operated on a supported GNU/Linux system from the terminal.

The repository does not define a graphical installer or desktop interface. Installation and administration are terminal operations.

The intended installation flow is:

```text
Install Node Core OS from the GNU/Linux terminal
        │
        ▼
Initialize Node
        │
        ▼
Configure local storage
        │
        ▼
Install / configure Kubo
        │
        ▼
Initialize Node Core Runtime
        │
        ▼
Node Core OS
```

# First Boot

After installation, the Node should enter the main interface:

```text
Node Core OS
byLAEV

0. Exit
1. Node Core BIOS
2. Node Core
3. Applications

>
```

The first administrative path is:

```text
Node Core BIOS
      │
      ├── Storage
      │
      └── IPFS / Kubo
              │
              ├── Install
              ├── Configure
              ├── Start
              ├── Stop
              └── Status
```

Once the infrastructure is operational:

```text
Node Core
      │
      ├── Add
      ├── CID
      ├── Pin
      ├── Publish
      └── Retrieve
```

The Node therefore becomes useful before any application is installed.

---

# Complete System Model

The intended long-term architecture can be represented as:

```text
                              NODE CORE OS
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
                  BIOS         NODE CORE     APPLICATIONS
                    │              │              │
                    │              │              ├── Programs
                    │              │              ├── Services
                    │              │              └── Protocols
                    │              │
                    │              ├── Storage
                    │              ├── Content
                    │              ├── Network
                    │              ├── Identity
                    │              ├── Reputation
                    │              ├── Protocols
                    │              └── Services
                    │
                    └──────────────┬───────────────
                                   │
                            NODE RUNTIME
                                   │
             ┌─────────────────────┼─────────────────────┐
             │                     │                     │
          STORAGE                NETWORK              SERVICES
             │
        ┌────┴────┐
        ▼         ▼
      LOCAL     KUBO/IPFS
     STORAGE
```

A more complete conceptual stack is:

```text
Applications
     │
     ▼
Protocols
     │
     ▼
Identity / Reputation / Trust
     │
     ▼
Node Core
     │
     ├── Content
     ├── Storage
     ├── Network
     ├── Services
     └── Capabilities
     │
     ▼
Node Core Runtime
     │
     ▼
Node Infrastructure
     │
     ├── Local Storage
     ├── Kubo / IPFS
     ├── Network
     └── Operating System
```

This is the intended direction of the project, while individual modules can mature independently.

---

# Decentralized Architecture Principles

Node Core OS is designed around several principles.

## 1. The Node is infrastructure

The Node should remain useful independently from applications.

## 2. Local and decentralized resources coexist

Local storage and IPFS are complementary resources.

## 3. Content is independently addressable

CIDs allow content to be referenced independently from a local path.

## 4. Identity is separate from reputation

An identity can exist without a reputation, and different systems can evaluate reputation differently.

## 5. Reputation is evidence-oriented

Reputation should be capable of being derived from attestations, interactions, history, and other evidence rather than requiring one universal score.

## 6. Applications are optional

The infrastructure should work before applications are installed.

## 7. Protocols are first-class consumers

The architecture is intended to support distributed and decentralized protocols, not only file management.

## 8. Infrastructure should be composable

Storage, identity, network, services, and content should be exposed as reusable Node capabilities.

## 9. Administrative and operational concerns remain separate

BIOS configures the Node; Node Core operates it.

## 10. Higher-level systems should not redefine the infrastructure

Identity, reputation, protocols, and applications should build on Node Core rather than becoming entangled with its low-level implementation.

---

# Development Scope

The project has a broad architectural target but should be implemented incrementally.

## Foundation

```text
1. Boot
2. Runtime
3. Configuration
4. Local Storage
5. Kubo / IPFS
6. Service lifecycle
7. Network foundation
8. Diagnostics
```

## Node Core

```text
9. Storage abstraction
10. Files
11. CID
12. Add
13. Retrieve
14. Pin / Unpin
15. Publish
16. Share
17. Utilities
```

## Identity

```text
18. Node identity
19. Key management
20. Identity records
21. Credentials
22. Identity-linked resources
23. Identity-aware operations
```

## Reputation and Trust

```text
24. Evidence model
25. Attestations
26. Trust relationships
27. Reputation records
28. Context-specific reputation
29. Reputation discovery and verification
```

## Protocols

```text
30. Protocol model
31. Protocol lifecycle
32. Protocol services
33. Inter-node communication
34. Distributed coordination
35. Protocol-specific identity and reputation
```

## Applications

```text
36. Application model
37. Installation
38. Permissions
39. Application lifecycle
40. Application services
41. Application storage
42. Application networking
```

## Advanced Node Systems

```text
43. Resource management
44. Discovery
45. Synchronization
46. Distributed services
47. Content discovery
48. Provenance
49. Inter-node trust
50. Node-to-node systems
```

The implementation order may change as the project develops. The architectural dependency direction should remain:

```text
Infrastructure
      ↓
Node Runtime
      ↓
BIOS / Node Core
      ↓
Identity / Content / Services
      ↓
Protocols
      ↓
Applications
      ↓
Application-specific systems
```

---

# Project Boundaries

Node Core OS is not intended to make every decentralized application part of the operating system.

Instead, it provides the common infrastructure those systems can rely on.

```text
                    Node Core OS
                         │
                Common Node Layer
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
   Protocol A        Protocol B        Protocol C
       │                 │                 │
       ▼                 ▼                 ▼
 Application A     Application B     Application C
```

This allows multiple protocols and applications to coexist on the same Node without requiring each one to reinvent storage, identity, networking, service management, or content addressing.

---

# Current Implementation State

The repository is in early development.

The architecture described here represents the **full intended design direction**, not a claim that every component is already implemented.

The project should distinguish clearly between:

- **Implemented** — functionality currently available in the repository.
- **In development** — functionality actively being implemented.
- **Architectural target** — components defined by the design but not yet implemented.
- **Future** — extensions that depend on mature lower layers.

The first functional milestone is to establish the Node foundation:

```text
Install
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

Identity, reputation, protocols, and applications are higher-level systems that can then be built on the stable Node foundation.

---

# Long-Term Vision

Node Core OS is intended to provide a general-purpose infrastructure for Nodes that can operate with both local and decentralized resources.

The long-term model is:

```text
                         NODE
                          │
             ┌────────────┴────────────┐
             │                         │
       Local Resources          Decentralized Resources
             │                         │
             └────────────┬────────────┘
                          │
                     Node Core
                          │
          ┌───────────────┼────────────────┐
          │               │                │
       Content         Identity         Services
          │               │                │
          │          Reputation            │
          │               │                │
          └───────────────┼────────────────┘
                          │
                       Protocols
                          │
                    Applications
```

The goal is not simply to create another file manager or IPFS wrapper.

The goal is to establish a coherent **Node infrastructure layer** over which decentralized protocols, services, identities, reputations, and applications can operate.

> **Node Core OS provides the Node.  
> Node Core provides the capabilities.  
> Protocols define distributed behavior.  
> Applications create higher-level experiences.**

---

# Project

**Node Core OS**  
byLAEV

Repository: https://github.com/byLAEV/Node-Core-OS/
