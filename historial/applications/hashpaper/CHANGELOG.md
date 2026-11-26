# HashPaper Changelog

## 0.3.2 — OpenTimestamps storage and repeat-operation safety

- Create new HashPaper originals in `storage/opentimestamps/`, keeping each `.ots` proof adjacent to its original.
- Continue listing and operating on originals already stored in `hashpaper/documents/`; existing documents and proof files are not moved or deleted.
- When a non-empty `.ots` proof already exists, a repeated `stamp` request verifies the existing proof and reports its actual status instead of submitting a duplicate or overwriting the evidence.
- Reject empty or non-file proof paths without deleting or replacing them.
- Add regression tests for existing-proof handling and canonical storage creation.


## 0.3.0 — Independent application updates

- Added a standalone updater that replaces only `applications/hashpaper/`, without reinstalling or replacing the Node Core OS application.
- Added pre-install compilation and unit-test checks, explicit user confirmation, an update lock, and rollback to the previous HashPaper code if post-install verification fails.
- Kept persistent documents, adjacent OpenTimestamps proofs, packages, publication receipts, identity, configuration, local storage, and the Kubo repository outside the updated application directory.
- Documented a direct installation path for the updater for existing Node Core OS installations, including installations that have not yet received the latest Node Core OS updater.
- No claim is made that live OpenTimestamps calendar submission or Bitcoin attestation has been verified by the unit tests.

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
- Added live Kubo installer E2E checks for publication, retrieval, and identity/Peer ID association.
- Added a manually triggered GitHub Actions workflow for real OpenTimestamps client/calendar submission and immediate proof checking using synthetic content. It preserves the distinction between pending timestamps and verified Bitcoin attestations. The Ubuntu 24.04 installer E2E workflow and GNU/Linux terminal CI passed on commit `d953d0732dba587b5a4153aba4b9758d656edf89`.
- HashPaper remains shipped with Node Core OS; a separate HashPaper installer has not been implemented.
- Encryption status: **NOT IMPLEMENTED**. Identity and document content included in packages are unencrypted.
- Live OpenTimestamps calendar submission and verified Bitcoin attestation are not yet claimed by CI.
