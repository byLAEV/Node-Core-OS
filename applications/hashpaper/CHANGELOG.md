# HashPaper Changelog

## 0.1.0 — Initial integrated milestone

- Added local UTF-8 text/Markdown document creation without overwriting existing originals.
- Added SHA-256 calculation over exact original bytes.
- Added transparent JSON package generation embedding the complete original text and known identity/node fields.
- Added an adapter around the official OpenTimestamps `ots` CLI for stamp, check/verify, and upgrade operations. The adapter distinguishes pending, verified, network-error, and proof-error states; automated tests use a fake executable.
- Added safe proof-backup behavior for upgrades, including preservation of a changed proof backup when an upgrade is interrupted.
- Added a Kubo/IPFS publisher using Node Core OS `ContentManager` and `KuboManager`, requiring explicit public-disclosure confirmation and checking CID retrieval, byte equality, SHA-256, and pin state.
- Added explicit local identity association using the saved Node Core OS identity profile and a live Kubo Peer ID after user confirmation.
- Added HashPaper to the Node Core OS Applications menu and implemented the interactive application menu for document creation, timestamp operations, package generation, and IPFS publication.
- Added automated tests for no-argument launcher behavior and interactive menu command dispatch.
- Added installer verification and compilation checks for HashPaper.
- Added persistent directories under `~/.node-core/hashpaper/{documents,proofs,packages,records}`.
- Expanded updater preservation checks for HashPaper documents, proofs, packages, and records during successful update and rollback scenarios.
- Added live Kubo installer E2E checks for publication, retrieval, and identity/Peer ID association. The Ubuntu 24.04 installer E2E workflow and GNU/Linux terminal CI passed on commit `d953d0732dba587b5a4153aba4b9758d656edf89`.
- HashPaper remains shipped with Node Core OS; a separate HashPaper installer has not been implemented.
- Encryption status: **NOT IMPLEMENTED**. Identity and document content included in packages are unencrypted.
- Live OpenTimestamps calendar submission and verified Bitcoin attestation are not yet claimed by CI.
