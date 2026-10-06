# Node Core OS

**Node Core OS** is a node infrastructure designed to manage local and decentralized storage as a unified environment for running protocols, services, and applications in a distributed and decentralized manner.

The project is built around a simple architectural principle:

> **The Node is the infrastructure. Node Core is the interface to that infrastructure. Applications are built on top of it.**

Node Core OS is designed to operate across two complementary storage environments:

- **Local Storage** — resources stored directly on the Node.
- **Kubo / IPFS** — decentralized, content-addressed storage and retrieval.

The objective is not to make these two environments compete with each other, but to provide a common Node-level abstraction through which both can be configured, operated, and used.

---

## Architecture

Node Core OS is organized into three visible levels:

```text
Node Core OS
│
├── Node Core BIOS
├── Node Core
└── Applications
```

These levels have different responsibilities.

```text
                    Node Core OS
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
       BIOS         Node Core     Applications
          │              │              │
   administration    operation       programs
          │              │              │
          └──────────────┼──────────────┘
                         │
                  Node Core Runtime
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        Local Storage           Kubo / IPFS
```

### Node Core BIOS

**Node Core BIOS is the administrative layer of the Node.**

It is inspired by the role of a BIOS: it is the place where the fundamental configuration and operational state of the Node are managed before higher-level use.

BIOS does not represent the everyday use of the Node's resources. It manages the infrastructure that makes those resources available.

The complete BIOS architecture is intended to include:

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

The initial implementation begins with Storage and IPFS / Kubo. The remaining modules define the intended administrative scope of the Node as the project evolves.

BIOS responsibilities include, depending on the module:

- configuring Node storage
- managing storage locations and state
- installing and configuring Kubo
- starting and stopping Kubo
- inspecting IPFS status
- managing Node services
- managing network configuration
- maintaining Node configuration
- diagnostics and health checks
- security configuration
- updates and lifecycle operations

> **BIOS configures the Node.**

---

## Node Core

**Node Core is the operational layer of the Node.**

Where BIOS manages how the Node exists and operates, Node Core exposes the capabilities of that Node for everyday use.

The intended operational surface is:

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

The initial implementation concentrates on the fundamental storage and IPFS operations.

The broader Node Core layer is intended to provide a stable abstraction over the underlying Node resources so that higher-level protocols and programs do not need to directly manage every infrastructure detail themselves.

> **BIOS configures the Node.  
> Node Core uses the Node.**

---

## Applications

Applications are the third architectural level.

They are intentionally separated from the Node Core itself.

```text
Applications
│
├── App 001
├── App 002
├── App 003
└── ...
```

A new installation does not require applications to exist.

The initial state is:

```text
Applications

No applications installed.

[Future]
```

This separation establishes an important boundary:

- **BIOS** manages infrastructure.
- **Node Core** provides infrastructure capabilities.
- **Applications** consume those capabilities.

Applications can therefore be developed independently from the fundamental Node infrastructure.

---

# Runtime Architecture

BIOS and Node Core are not intended to become two independent systems.

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
                 ┌───────┴───────┐
                 ▼               ▼
           Local Storage      Kubo / IPFS
```

The Runtime is the common technical foundation responsible for connecting the user-facing architecture with the resources of the Node.

This separation prevents BIOS and Node Core from duplicating infrastructure logic.

---

# Storage Architecture

Storage is one of the fundamental concepts of Node Core OS.

The Node is designed to operate with two complementary storage environments:

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

Local Storage represents resources physically or logically stored on the Node.

It provides the Node with direct access to local files and data.

Its responsibilities can include:

- storage paths
- file management
- local capacity
- local state
- local persistence
- local retrieval

## Kubo / IPFS

Kubo provides the IPFS implementation used by Node Core OS.

IPFS introduces content-addressed storage and decentralized retrieval into the Node.

Node Core OS therefore treats Kubo as an infrastructure component rather than as the entire Node Core architecture.

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

One of the central operational flows of Node Core OS is:

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
 │
 ├── Publish
 │
 └── Retrieve
```

A file can therefore move from a local representation into a content-addressed representation.

The CID becomes a stable reference to the content rather than a reference based only on its local filesystem path.

This creates the foundation for future decentralized protocols and applications that can reference and exchange content independently from a single local filesystem.

---

# Node Lifecycle

The Node is intended to have a lifecycle that can eventually be managed from BIOS.

```text
Install
   │
   ▼
Initialize
   │
   ▼
Boot
   │
   ▼
Node Core Runtime
   │
   ├── Initialize Storage
   │
   ├── Initialize Services
   │
   └── Initialize Kubo / IPFS
   │
   ▼
Node Ready
   │
   ├── BIOS
   ├── Node Core
   └── Applications
   │
   ▼
Shutdown / Maintenance / Update
```

The first implementation does not need to implement every lifecycle state immediately. The architecture reserves the space for them so that the Node can evolve without changing its fundamental model.

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

The initial BIOS interface:

```text
Node Core BIOS
byLAEV

0. Back
1. Storage
2. IPFS / Kubo

>
```

The intended complete administrative interface can grow toward:

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

>
```

## Node Core

The initial operational interface:

```text
Node Core
byLAEV

0. Back
1. Storage
2. IPFS
3. Files
4. CID
5. Pin
6. Retrieve

>
```

The broader operational interface can evolve toward:

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
10. Utilities

>
```

The menu is an interface to the architecture, not the architecture itself. Internal modules should remain independent of the presentation layer.

---

# Installation and First Boot

Node Core OS is initially designed as a Node infrastructure layer installed on top of an existing operating system.

The first installation flow is intended to be:

```text
Install Node Core OS
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
Start Node Core Runtime
        │
        ▼
Node Core OS
```

After installation, the user should be able to enter BIOS and inspect the Node before using its operational capabilities.

The intended first-use sequence is:

```text
Node Core OS
      │
      ▼
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
                      │
                      ▼
                  Node Core
                      │
                      ├── Add
                      ├── CID
                      ├── Pin
                      ├── Publish
                      └── Retrieve
```

---

# Design Boundaries

Node Core OS deliberately separates several concerns.

## BIOS is not Node Core

BIOS is concerned with infrastructure administration.

Node Core is concerned with using the capabilities provided by that infrastructure.

```text
BIOS
  │
  └── How does the Node exist and operate?

Node Core
  │
  └── What can I do with the Node?
```

## Node Core is not Applications

Node Core provides common capabilities.

Applications use those capabilities to implement higher-level behavior.

```text
Node Core
     │
     ├── Storage
     ├── Files
     ├── IPFS
     ├── CID
     └── Retrieval
            │
            ▼
      Applications
```

This prevents application-specific requirements from becoming part of the fundamental Node infrastructure.

---

# Long-Term Architecture

The long-term scope of Node Core OS extends beyond file storage.

The intended direction is a general-purpose infrastructure for running protocols and programs over a Node that can coordinate local and decentralized resources.

```text
                         Node Core OS
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
         BIOS              Node Core         Applications
          │                   │                   │
          │                   │                   ├── Protocols
          │                   │                   ├── Services
          │                   │                   └── Programs
          │                   │
          └──────────┬────────┘
                     │
               Node Runtime
                     │
        ┌────────────┼────────────┐
        │            │            │
     Storage       Network      Services
        │
   ┌────┴────┐
   │         │
 Local     IPFS
Storage   / Kubo
```

This foundation can later support additional systems without changing the fundamental three-level architecture.

Potential future layers include:

- identity
- permissions
- trust and reputation
- decentralized services
- protocol execution
- application installation
- application lifecycle
- inter-node communication
- distributed coordination
- additional storage backends
- resource management
- data publishing and discovery

These are future capabilities, not prerequisites for the first functional Node.

---

# Identity and Higher-Level Systems

Identity, reputation, and other higher-level systems are intentionally not part of the initial Node infrastructure.

They can be introduced after the underlying Node has a stable way to:

1. exist
2. store data
3. communicate with IPFS
4. address content
5. retrieve content
6. run services
7. expose capabilities to applications

This establishes a bottom-up architecture:

```text
Infrastructure
      │
      ▼
Node
      │
      ▼
Storage + Network + Services
      │
      ▼
Node Core
      │
      ▼
Protocols
      │
      ▼
Applications
      │
      ▼
Higher-level systems
```

---

# Development Strategy

The project should be developed from the infrastructure upward.

## Foundation

```text
1. Boot
2. Runtime
3. Configuration
4. Local Storage
5. Kubo / IPFS
6. Service lifecycle
```

## Node Core

```text
7. Storage abstraction
8. Files
9. CID
10. Add
11. Retrieve
12. Pin / Unpin
13. Publish
14. Share
```

## Applications

```text
15. Application model
16. Application installation
17. Application lifecycle
18. Application permissions
19. Application services
```

## Higher-level systems

```text
20. Identity
21. Trust / Reputation
22. Protocols
23. Distributed services
24. Inter-node systems
```

The sequence can evolve as implementation experience reveals better boundaries, but the dependency direction should remain:

```text
Infrastructure
      ↓
Node Runtime
      ↓
BIOS / Node Core
      ↓
Applications
      ↓
Protocols and higher-level systems
```

---

# Project Philosophy

Node Core OS is intended to make a Node understandable and composable.

The project does not begin by defining every application that could run on it. It begins by defining the infrastructure that applications can rely on.

The fundamental abstraction is:

```text
                 NODE
                  │
        ┌─────────┴─────────┐
        │                   │
     Local              Decentralized
    Resources             Resources
        │                   │
        └─────────┬─────────┘
                  │
             Node Core
                  │
        ┌─────────┼─────────┐
        │         │         │
     Protocols  Services  Applications
```

The Node should therefore be useful before any application is installed.

Applications are optional.

The Node infrastructure is fundamental.

---

# Current Scope

The repository is in early development.

The architecture described in this document represents the intended design and implementation direction. The project should distinguish clearly between:

- **implemented functionality**
- **planned architecture**
- **future extensions**

The initial implementation is centered on establishing a functional Node with local storage and Kubo/IPFS integration.

The long-term goal is a general Node infrastructure capable of supporting distributed and decentralized protocols and programs through a common, extensible architecture.

---

# Project

**Node Core OS**  
byLAEV

Repository: https://github.com/byLAEV/Node-Core-OS/
