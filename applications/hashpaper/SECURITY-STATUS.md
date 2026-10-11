# HashPaper Security and Transparency Status

**Current status: integrated prototype; encryption is NOT IMPLEMENTED.**

## Implemented and tested

- HashPaper shows a public-disclosure warning and requires typing `PUBLISH` before publishing a package.
- The package must contain the complete original text. The original document SHA-256 is calculated from the exact original bytes.
- The publisher uses Node Core OS content/Kubo interfaces, retrieves the returned CID, compares retrieved bytes against the local package, verifies the SHA-256, and checks pin state.
- Identity inclusion through `--use-node-profile` requires an existing local Node Core OS profile, a live Kubo Peer ID, review of the original text and profile fields, and explicit confirmation before association.
- GitHub Actions has passed the Ubuntu 24.04 installer E2E workflow in both service modes, including a live Kubo package publication/retrieval test and a live Peer ID association test using synthetic identity data.
- The updater preservation tests check HashPaper documents, proofs, packages, and records across successful update and rollback scenarios.
- The official OpenTimestamps CLI is invoked by an adapter. Automated tests use a fake executable and do not prove live calendar or Bitcoin attestation verification.

## Explicit transparency decisions

- Identity fields included in a HashPaper record are unencrypted.
- The IPFS package intentionally contains the complete original text submitted to OpenTimestamps.
- OTS metadata is included only when supplied by an actual client report; HashPaper must not fabricate block height, confirmations, verification outcomes, CIDs, or pin state.
- The original document bytes are hashed with SHA-256 before timestamp submission. This is not the hash of the larger package.
- Public IPFS publication can disclose document text and included identity fields to third parties.

## Identity and evidence boundaries

A profile marked `declared` is not a verified civil identity. A node Peer ID identifies a technical node and does not prove who controls it. An OpenTimestamps proof does not by itself establish authorship, truth, ownership, or civil identity. A CID identifies content but does not alone prove legal validity or permanent availability.

## Remaining validation

- A GitHub Actions workflow now exists for real OpenTimestamps submission and immediate checking using synthetic content. It can be run manually and is scheduled weekly after merge to the default branch; creating a proof or receiving a pending result does not establish a verified Bitcoin attestation.
- A separate HashPaper installer has not been implemented; HashPaper is shipped with Node Core OS.
- Future releases must keep checking that application data remains outside the replaceable code tree and survives upgrades and rollback.

## Future encryption

Encryption is deliberately not implemented now. Future encryption must have an explicit threat model, key-management contract, format/schema versioning, and migration tests. Existing transparent records must not be described as encrypted retroactively.
