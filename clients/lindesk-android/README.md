# Lindesk Android client

Lindesk is a separate Android client for authenticated access to GNU/Linux Node Core OS nodes and user-approved Linux installation/deployment flows. It does not execute the Node Core OS runtime on Android or Termux.

## Interface boundary

- Connect through a documented, versioned Node Core API.
- Never expose Kubo administrative RPC directly.
- Never silently export Linux node private keys.
- Remote installation actions must disclose target, commands, privilege requirements and obtain explicit user approval.

This folder is the destination module. Android implementation files are migrated here only with their build configuration and tests.
