# HashPaper Changelog

## 0.1.0 — Initial local foundation

- Added a local-first UTF-8 text/Markdown document creation primitive that refuses to overwrite an existing original.
- Added SHA-256 calculation over exact original bytes.
- Added a transparent JSON package model that embeds the complete original text and includes known identity/node fields without inventing missing values.
- Added tests for byte integrity, no-overwrite behavior, transparent identity inclusion, non-UTF-8 rejection, and package serialization.
- Added an explicit `--use-node-profile` flow that requires an existing Node Core identity profile and a live Kubo Peer ID, shows the full document and identity fields, requests exact confirmation, and only then persists the local node association.
- Encryption status: **NOT IMPLEMENTED**. Identity and document content are not encrypted.
- Added a wrapper around the official `ots` CLI for stamp, check/verify, and upgrade operations. The wrapper does not implement cryptography; tests use a fake CLI executable, so real network timestamping has not yet been verified.
- Added a Kubo/IPFS publisher adapter through Node Core OS `ContentManager` and `KuboManager`; it requires explicit publication confirmation, compares retrieved bytes, and checks pin state. Unit tests use a fake runtime; live Kubo publication is not yet verified.
- Added the HashPaper entry to the Node Core OS Applications menu.
- Installer verification checks the HashPaper entry point and compiles the application package.
- Node Core OS creates persistent HashPaper directories outside the replaceable app-code tree.
- Extended updater preservation tests to check documents, proofs, packages, and records across update and rollback scenarios.
- A separate HashPaper installer is not yet implemented; HashPaper is shipped with the main Node Core OS code tree.
- Main installer/updater integration: **NOT IMPLEMENTED**.
