# HashPaper Changelog

## 0.1.0 — Initial local foundation

- Added a local-first UTF-8 text/Markdown document creation primitive that refuses to overwrite an existing original.
- Added SHA-256 calculation over exact original bytes.
- Added a transparent JSON package model that embeds the complete original text and includes known identity/node fields without inventing missing values.
- Added tests for byte integrity, no-overwrite behavior, transparent identity inclusion, non-UTF-8 rejection, and package serialization.
- Encryption status: **NOT IMPLEMENTED**. Identity and document content are not encrypted.
- OpenTimestamps submission/verification: **NOT IMPLEMENTED**.
- Kubo/IPFS publication and retrieval verification: **NOT IMPLEMENTED**.
- Main installer/updater integration: **NOT IMPLEMENTED**.
