# HashPaper for Node Core OS

## Normative functional manifest

For a detailed menu-by-menu and command-by-command description, source mapping, storage/read/write behavior, expected output, security boundaries, failure handling, and audit test matrix, see the **[HashPaper Functional Manifest and Audit Guide](HASHPAPER-FUNCTIONAL-MANIFEST.md)**. This document remains a higher-level overview; the manifest defines the detailed audit procedure. A documented expectation is not a test result: verify the implementation and the CI run for the exact commit.

## Purpose

HashPaper is an application included in the Node Core OS repository. It creates a local original, calculates SHA-256 over its exact bytes, delegates timestamp operations to the official OpenTimestamps client, assembles a transparent evidence package, and publishes that package through the existing Kubo/IPFS content layer after explicit confirmation.

## Current implementation status

The application lives in `applications/hashpaper/` and has a CLI, an interactive menu opened from the Node Core OS Applications menu, unit tests, installer verification, persistent data directories, and updater preservation tests.

Verified in GitHub Actions on commit `d953d0732dba587b5a4153aba4b9758d656edf89`:

- GNU/Linux terminal CI passed.
- Ubuntu 24.04 installer E2E passed in both service modes.
- Clean installation and installed filesystem checks passed.
- HashPaper package publication through a live Kubo daemon passed.
- The package was retrieved by CID and its bytes matched the local package.
- Identity association against the live Kubo Peer ID passed using synthetic identity data.
- Uninstall safety and uninstall checks passed.

The OpenTimestamps adapter invokes the official `ots` CLI for `stamp`, `check`, and `upgrade`. Unit tests use a fake executable. A workflow, `.github/workflows/hashpaper-opentimestamps-live.yml`, now installs the official client and attempts a real submission/check using synthetic data. It supports manual execution and a weekly schedule after merge to the default branch. Its result must be inspected; a pending result does not establish a verified Bitcoin attestation. A separate HashPaper installer has not been implemented; HashPaper ships with Node Core OS.

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

Node Core OS keeps persistent HashPaper data outside the replaceable application-code tree. New original documents and their adjacent `.ots` proofs use the local-storage namespace:

```text
~/.node-core/
├── storage/
│   └── opentimestamps/
│       ├── Genesis-HashPaper.md
│       └── Genesis-HashPaper.md.ots
└── hashpaper/
    ├── documents/   # legacy originals remain discoverable in place
    ├── ipfs/
    ├── packages/
    └── records/
```

HashPaper's document history searches both `storage/opentimestamps/` and the legacy `hashpaper/documents/` directory. Existing originals and proofs are not automatically moved. The updater preservation test seeds and checks persistent data through successful update and rollback scenarios. HashPaper is launched from the Applications menu and its files are checked by installer verification.

A repeated `stamp` request does not overwrite or re-submit a non-empty existing `.ots` file. It runs the official client's verification operation against that original and reports the returned state. A pending proof remains pending; a proof is reported as verified only when the official client confirms it against the original. An empty `.ots` path is preserved and reported as an error for explicit repair.

## Remaining release validation

- Test live OpenTimestamps calendar submission with synthetic content.
- Recheck the resulting proof after an attestation becomes available, and claim `VERIFIED` only after the official client verifies it against the original document.
- Continue validating updater preservation and failure paths as the updater evolves.
- Do not claim encryption, civil identity verification, authorship, or truth from a hash, CID, Peer ID, or timestamp alone.

## OpenTimestamps evidence lifecycle and continuity

OpenTimestamps confirmation may take hours or days. A proof that is pending confirmation is an expected intermediate state, not a verification failure. HashPaper must not assume that a Bitcoin transaction ID exists, that a transaction is in the mempool, or that a Bitcoin block attestation is available before the official client reports it.

Every timestamp report records the SHA-256 fingerprint of the original document and, when a non-empty proof exists, the SHA-256 fingerprint of the exact local `.ots` proof. These are local integrity fingerprints, not identifiers issued by OpenTimestamps or Bitcoin. A proof upgrade records the prior proof fingerprint when the bytes change, while the existing `.before-upgrade` backup preserves the prior proof bytes. This lets operators compare evidence across upgrade attempts without discarding the earlier proof.

HashPaper exposes calendar URLs and Bitcoin transaction IDs only when those values are explicitly present in the official client's captured output. It does not infer a transaction ID from an arbitrary 64-character hash, manufacture missing identifiers, or interpret a calendar URL as proof of Bitcoin confirmation. The captured standard output and standard error remain available for inspection. An identifier that the official client does not expose is reported as unavailable; the application must not pretend that it extracted all internal proof fields.

Use the following lifecycle:

1. **Submission:** retain the original document, its SHA-256, the created `.ots` proof, its SHA-256, and any calendar URLs or explicitly labelled transaction IDs actually printed by the official client. The status remains unverified.
2. **Pending period:** rerun `check` to ask the official client to verify the current proof. If it reports pending Bitcoin confirmation, preserve that state and the available evidence. Network failures must remain distinguishable from pending confirmation.
3. **Upgrade:** run `upgrade` only when appropriate. Preserve the prior proof when the proof bytes change. An upgrade result such as “Timestamp is complete” is not, by itself, a successful verification against the original document.
4. **Verification:** run `check` after upgrade. Report `VERIFIED` only when the official verifier reports a Bitcoin block attestation for the proof. Record the reported block height and current proof fingerprint. Never claim a block height that was not returned by the verifier.
5. **Continuity:** retain the original document fingerprint, prior and current proof fingerprints, captured client output, and any available identifiers. These fingerprints support comparison of local artifacts; they do not replace official OpenTimestamps verification or independently prove that an identifier belongs to a particular transaction.

The `proof_sha256`, `previous_proof_sha256`, `calendar_urls`, and `bitcoin_transaction_ids` fields are additive report metadata. Empty identifier lists mean the official output did not expose a matching identifier; they do not mean no such identifier exists internally. The parser is intentionally conservative.

Unit tests use a fake `ots` executable and validate metadata extraction and proof continuity. They do not establish that a real calendar accepted a submission, that a transaction entered the mempool, or that a Bitcoin block confirmed a timestamp. Real-network validation must be reported separately and must not be represented as successful until the official verifier returns a confirmed attestation.

