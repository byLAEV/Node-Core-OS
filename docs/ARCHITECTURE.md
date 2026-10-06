# Node Core OS — Implementation Architecture

This document translates the README's conceptual architecture into repository
boundaries.

## Dependency direction

Infrastructure -> Runtime -> BIOS/Core -> Protocols/Identity/Content -> Applications.

The presentation layer must not own storage, IPFS, identity, or protocol logic.

## Initial modules

- `node_core.runtime`: lifecycle and dependency composition.
- `node_core.config`: persistent configuration and filesystem layout.
- `node_core.storage`: local storage abstraction.
- `node_core.ipfs`: Kubo/IPFS adapter boundary.
- `node_core.ui`: terminal presentation layer.
- `identity/`, `reputation/`, `protocols/`, `services/`: reserved extension boundaries.

## First functional path

Boot -> initialize local storage -> expose BIOS/Core menus -> inspect Kubo ->
add/retrieve content -> introduce identity -> introduce evidence/reputation ->
protocols -> applications.

A placeholder is deliberately preferable to a fake implementation: higher layers
must not bypass the boundaries established here.
