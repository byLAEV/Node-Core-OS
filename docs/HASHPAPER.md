# HashPaper for Node Core OS

## Purpose

HashPaper is an application included in the Node Core OS repository. It creates a local original, calculates SHA-256 over its exact bytes, delegates timestamp operations to the official OpenTimestamps client, assembles a transparent evidence package, and publishes that package through the existing Kubo/IPFS content layer after explicit confirmation.

## Current implementation status

The application lives in `applications/hashpaper/` and has a CLI, unit tests, an Applications-menu entry, installer verification, persistent data directories, and updater preservation tests.

Verified in GitHub Actions on commit `d953d0732dba587b5a4153aba4b9758d656edf89`:

- GNU/Linux terminal CI passed.
- Ubuntu 24.04 installer E2E passed in both service modes.
- Clean installation and installed filesystem checks passed.
- HashPaper package publication through a live Kubo daemon passed.
- The package was retrieved by CID and its bytes matched the local package.
- Identity association against the live Kubo Peer ID passed using synthetic identity data.
- Uninstall safety and uninstall checks passed.

The OpenTimestamps adapter invokes the official `ots` CLI for `stamp`, `check`, and `upgrade`. Its automated tests use a fake executable. Live calendar submission and later verified Bitcoin attestation have not yet been demonstrated by CI and remain explicit validation work. A separate HashPaper installer has not been implemented; HashPaper ships with Node Core OS.

## Artifact contract

1. **Original document** — UTF-8 text or Markdown. HashPaper calculates SHA-256 over its exact bytes. Existing originals are not overwritten by document creation; an edit should create a new version.
2. **OpenTimestamps proof** — the `.ots` file created and updated by the official client. Existence of the file is not proof verification. Pending confirmation, network errors, available attestation, and successful verification are distinct states.
3. **IPFS package** — versioned transparent JSON containing the complete original text, included identity/node fields, original byte length and SHA-256, and OTS report fields actually provided by the client. The original hash is not the package hash. The publication receipt stores the CID separately because embedding the package's own CID would change the content and CID.

If timestamp metadata changes, create a new package version and CID; do not imply that a CID is mutable.

## Identity and node semantics

The Node Core OS profile schema includes `identity_id`, `full_name`, `alias`, `nationality`, `issuing_country`, `document_type`, `document_number`, `birth_date`, `height_cm`, `gender`, `identity_status`, `node_id`, `created_at`, and `updated_at`. HashPaper must not invent missing values.

The `package --use-node-profile` flow requires an existing local identity profile and a live Kubo Peer ID. It displays the complete original text and profile fields, requires the exact confirmation `INCLUDE IDENTITY AND NODE`, and then saves the local association and creates the package. Publication is a separate action that requires typing `PUBLISH`.

A profile marked `declared` is not independently verified civil identity. A Peer ID is a technical node identifier and does not establish who controls it.

## Transparency and encryption

Encryption is **NOT IMPLEMENTED**. The package intentionally includes the complete original text and selected identity fields in cleartext. Anyone able to retrieve the public IPFS content can read those fields. Use synthetic data for tests; real identity data must not be published accidentally. Future encryption requires a separately specified policy and key-management model. Relevant documentation and changelog entries must explicitly state encryption status.

## Persistent data and updater

Node Core OS creates HashPaper directories outside the replaceable application-code tree:

```text
~/.node-core/hashpaper/
├── documents/
├── proofs/
├── packages/
└── records/
```

The updater preservation test seeds and checks these data categories through successful update and rollback scenarios. HashPaper is launched from the Applications menu and its files are checked by installer verification.

## Remaining release validation

- Test live OpenTimestamps calendar submission with synthetic content.
- Recheck the resulting proof after an attestation becomes available, and claim `VERIFIED` only after the official client verifies it against the original document.
- Continue validating updater preservation and failure paths as the updater evolves.
- Do not claim encryption, civil identity verification, authorship, or truth from a hash, CID, Peer ID, or timestamp alone.
