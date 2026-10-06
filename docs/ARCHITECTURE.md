# Node Core OS — Implementation Architecture

Infrastructure -> Runtime -> BIOS/Core -> Content Registry -> Identity/Protocols -> Applications.

## Node Core BIOS

BIOS is the administrative boundary of the Node.

### Storage

Storage owns the local Node storage root and safe filesystem access. Its state is
independent from the Kubo repository.

### IPFS / Kubo

BIOS owns Kubo infrastructure:

Detect -> Initialize -> Configure -> Start -> Status -> Stop

Kubo is treated as an external node service. Node Core does not reimplement Kubo
or expose its administrative RPC as the application API.

## Node Core Content v1

The completed content path is:

Add -> CID -> Registry -> Publish -> Share
                         |        |
                         |        +-> ipfs://CID
                         |        +-> gateway /ipfs/CID
                         |
                         +-> Pin / Unpin
                         |
                         +-> Retrieve

### CID Registry

The local registry is Node Core's durable index of content it knows about. It is
not a replacement for IPFS and does not become the source of truth for content.

Current record fields:

- CID
- name
- size
- creation timestamp
- pin state
- original local source path
- optional owner identity
- provenance metadata
- publication timestamp
- publication mode

Registry storage:

~/.node-core/storage/registry/content.json

### Publication semantics

Content v1 deliberately uses **CID publication**, not IPNS. Publish records that
a registered resource is published by the Node Core content layer and pins it by
default so the local Kubo node retains it.

Share produces portable references from the CID. It does not grant permissions and
does not expose the administrative Kubo RPC.

IPNS/key-backed naming belongs above this layer because it will require identity and
cryptographic key management.

## Storage layout

~/.node-core/
  config.json
  storage/
    registry/
      content.json
  ipfs/
