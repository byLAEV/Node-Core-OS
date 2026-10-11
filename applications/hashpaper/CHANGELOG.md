# HashPaper Changelog

## 0.1.0 — Initial local foundation

- Added a local-first UTF-8 text/Markdown document creation primitive that refuses to overwrite an existing original.
- Added SHA-256 calculation over exact original bytes.
- Added a transparent JSON package model that embeds the complete original text and includes known identity/node fields without inventing missing values.
- Added tests for byte integrity, no-overwrite behavior, transparent identity inclusion, non-UTF-8 rejection, and package serialization.
- Encryption status: **NOT IMPLEMENTED**. Identity and document content are not encrypted.
- Added a wrapper around the official `ots` CLI for stamp, check/verify, and upgrade operations. The wrapper does not implement cryptography; tests use a fake CLI executable, so real network timestamping has not yet been verified.
- Added a Kubo/IPFS publisher adapter through Node Core OS `ContentManager` and `KuboManager`; it requires explicit publication confirmation, compares retrieved bytes, and checks pin state. Unit tests use a fake runtime; live Kubo publication is not yet verified.
- Installer/updater integration: **NOT IMPLEMENTED**.
- Main installer/updater integration: **NOT IMPLEMENTED**.
