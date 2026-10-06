# Node Core OS — Implementation Architecture

Infrastructure -> Runtime -> BIOS/Core -> Protocols/Identity/Content -> Applications.

## Node Core BIOS

BIOS is the administrative boundary of the Node.

### Storage

Storage owns the local Node storage root and safe filesystem access. Its state is
independent from the Kubo repository.

### IPFS / Kubo

BIOS owns Kubo infrastructure:

Detect -> Initialize -> Configure -> Start -> Status -> Stop

Kubo is treated as an external node service. Node Core does not reimplement Kubo
or start arbitrary processes outside this boundary.

## Node Core Content

Node Core now exposes the first end-to-end content capabilities:

Add -> CID -> Retrieve
          |
          +-> Pin
          |
          +-> Unpin

ContentManager is the Node Core abstraction. It accepts local files, sends them
to Kubo RPC /api/v0/add, returns a CID reference, retrieves content through
/api/v0/cat, and controls local pins through /api/v0/pin/add and
/api/v0/pin/rm.

For explicit separation of Add from persistence policy, Node Core sends pin=false
unless the caller requests immediate pinning.

The Kubo RPC remains local/admin-only and is never exposed as the application
interface.

## Storage layout

~/.node-core/
  config.json
  storage/       Node local storage
  ipfs/          Kubo repository

## Next architectural layer

After content is stable, the next layer is identity-aware content and action
records. Content should gain provenance without making the storage implementation
itself depend on identity.
