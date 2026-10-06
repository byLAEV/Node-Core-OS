# Node Core OS — Implementation Architecture

Infrastructure -> Runtime -> BIOS/Core -> Content Registry -> Identity/Protocols -> Applications.

## Content Registry

Node Core maintains a durable local index at `~/.node-core/storage/registry/content.json`.
It is an index, not a replacement for IPFS or the content source of truth.

Each record contains:
- CID
- name and size
- creation timestamp
- pin state
- original local source path
- optional owner identity
- provenance metadata placeholder

The registry uses atomic replacement when persisting its JSON file. Pin/unpin updates
the local record only after the corresponding Kubo operation succeeds.

## Identity-ready boundary

Identity is intentionally not implemented inside Storage or Kubo. The registry already
has owner/provenance fields so a later identity layer can attach signed actor/action
metadata without changing the storage abstraction.

## Flow

Add -> Kubo -> CID -> Registry
                         |
                    Pin / Unpin
                         |
                      Retrieve
