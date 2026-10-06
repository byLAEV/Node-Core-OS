# Node Core OS — Implementation Architecture

Infrastructure -> Runtime -> BIOS/Core -> Protocols/Identity/Content -> Applications.

## Node Core BIOS

BIOS is the administrative boundary of the Node. The first implementation
provides two real infrastructure domains:

- Storage: owns the local Node storage root and safe filesystem access.
- IPFS / Kubo: owns Kubo repository initialization, configuration profile,
  daemon startup, status, and graceful shutdown.

BIOS does not implement content operations. Those belong to Node Core.

## Kubo boundary

Kubo is treated as an external infrastructure service. Node Core does not
reimplement Kubo and does not assume that the Kubo process is the application.

Lifecycle:

Detect executable -> Initialize repository -> Apply import profile ->
Start daemon -> RPC health / PeerID / Version -> Running -> Shutdown

The Kubo repository is independent from Node local content:

~/.node-core/
  config.json
  storage/       Node local storage
  ipfs/          Kubo repository

This separation prevents local content management from implicitly destroying
the Kubo repository.

## First functional path

Boot -> initialize local storage -> BIOS -> initialize Kubo -> start Kubo ->
health check -> Node Core -> content/CID operations.
