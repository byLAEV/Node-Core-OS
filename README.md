# Node Core OS

Node Core OS is an infrastructure for running protocols and programs in a distributed and decentralized manner.

It provides a unified management and abstraction layer between local storage and decentralized storage based on Kubo/IPFS.

## Architecture

Node Core OS is organized into three levels:

```text
Node Core OS
│
├── Node Core BIOS
├── Node Core
└── Applications
```

The first two levels are active in the initial implementation. Applications remain an extension point for future development.

### Node Core BIOS

BIOS is the administrative layer of the Node.

It defines how the Node exists and how its underlying infrastructure is configured and operated.

Initial BIOS modules:

```text
Node Core BIOS
│
├── Storage
└── IPFS / Kubo
```

BIOS is responsible for tasks such as configuring local storage and installing, configuring, starting, stopping, and inspecting Kubo/IPFS.

> BIOS configures the Node.

### Node Core

Node Core is the operational layer.

It exposes the capabilities provided by the Node for everyday use.

Initial capabilities:

```text
Node Core
│
├── Storage
├── IPFS
├── Files
├── CID
├── Pin
└── Retrieve
```

> Node Core uses the Node.

### Applications

Applications are intentionally empty in the initial version.

```text
Applications

No applications installed.

[Future]
```

Applications will be able to consume the infrastructure and capabilities exposed by Node Core.

## Runtime Architecture

BIOS and Node Core are interfaces over a common Node Core Runtime.

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
           Local Storage      Kubo/IPFS
```

The Runtime provides the common foundation used by BIOS and Node Core.

## Version 0.1

The first implementation focuses on establishing a functional Node rather than implementing the complete future operating environment.

The initial milestone is:

```text
Install
  │
  ▼
Boot
  │
  ▼
Node Core OS
  │
  ├──────────────┐
  ▼              ▼
BIOS            Core
  │
  ▼
Storage
  │
  ▼
Kubo / IPFS
  │
  ├── Install
  ├── Configure
  ├── Start
  └── Status
             │
             ▼
            Core
             │
             ├── Add
             ├── CID
             ├── Pin
             └── Retrieve
```

A Node Core OS v0.1 installation is considered functional when it can:

1. Boot into the Node Core OS interface.
2. Manage local storage.
3. Install and configure Kubo/IPFS.
4. Start and inspect the Kubo/IPFS service.
5. Add a file to IPFS.
6. Obtain its CID.
7. Pin the content.
8. Retrieve the content through Node Core.

## Initial Interface

### Main Menu

```text
Node Core OS
byLAEV

0. Exit
1. Node Core BIOS
2. Node Core
3. Applications
```

### Node Core BIOS

```text
Node Core BIOS
byLAEV

0. Back
1. Storage
2. IPFS / Kubo
```

### Node Core

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
```

### Applications

```text
Applications
byLAEV

No applications installed.

[Future]
```

## Storage Model

Node Core OS is designed around two complementary storage environments:

```text
                 Node Core
                     │
              Storage Abstraction
                     │
             ┌───────┴───────┐
             │               │
        Local Storage      IPFS
```

Local storage provides direct storage on the Node.

Kubo/IPFS provides decentralized content-addressed storage and retrieval.

Node Core provides the interface through which both environments can be used.

## Project Direction

Node Core OS is intended to become a foundation for running protocols and programs over a Node that can manage both local and decentralized resources.

The initial implementation deliberately avoids introducing higher-level concepts such as identity, reputation, or applications before the underlying Node infrastructure is functional.

The development sequence therefore begins with:

```text
Node Core OS
    │
    ├── Boot
    ├── Storage
    ├── Kubo / IPFS
    ├── Node Core
    └── Applications
```

Higher-level systems can be built on top of this foundation later.

## Status

Early development.

The repository currently contains the project definition and is being developed toward the first functional Node Core OS implementation.
