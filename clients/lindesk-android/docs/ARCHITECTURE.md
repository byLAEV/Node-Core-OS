# Lindesk Android architecture

Lindesk is a separately built Android client. It does not bundle or execute the Node Core OS runtime.

## Trust boundary

- Connect to a GNU/Linux node through a documented versioned API.
- Authenticate the user and authorize each privileged operation.
- Display the target node, action, scope and consequences before installation or administration.
- Do not expose Kubo's administrative RPC endpoint to the public network.
- Do not export node private keys or sensitive local evidence by default.
- Treat local Android storage as client state, not the Linux node's authoritative storage.

## Migration state

This document defines the client boundary. Android source/build files have not yet been migrated into this destination; do not infer a buildable app from this scaffold alone.
