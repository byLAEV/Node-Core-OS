# Architecture

## Core boundary

The core provides a small command-line runtime and stable service boundaries. Applications are separate modules and must not be imported automatically by the core.

## Storage

- Local storage is the authoritative default for newly created data.
- The default user data directory is `~/.local/share/node-core-os`.
- Configuration and runtime state are separate from application payloads.
- IPFS/Kubo is an optional external service. The first release exposes no implicit upload or pin operation.

## Platform adapters

Platform detection is informational. Paths, service managers, and optional dependencies must be selected through explicit adapters, not terminal-emulator names.

## Security and transparency

- Display data locations and errors clearly.
- Do not silently transmit, publish, or delete user data.
- Keep secrets out of logs.
- Add advanced cryptographic privacy controls only after functional contracts and threat models are testable.
