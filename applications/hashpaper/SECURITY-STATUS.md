# HashPaper Security and Transparency Status

**Status: prototype; no encryption implemented.**

## Explicit current-stage decisions

- Identity fields included in a HashPaper record are transparent and unencrypted.
- The IPFS package is intended to contain the full original text submitted to OpenTimestamps, not only a digest or reference.
- Real OpenTimestamps proof bytes and metadata are included only when actually available from the official client and checked by the application.
- Unknown values must remain explicit (`null`, `PENDING`, or `NOT_CHECKED`); the application must never fabricate Bitcoin block details, confirmation counts, verification outcomes, CIDs, or pin state.
- The original document bytes are hashed with SHA-256 before timestamp submission. The hash is for the original document, not the larger package generated later.
- Publishing identity fields and document contents through IPFS can expose them to third parties. IPFS is not a confidentiality mechanism.

## Identity and evidence boundaries

A profile marked `declared` is not a verified civil identity. A node Peer ID is a technical identifier and does not prove who operates it. An OpenTimestamps proof is not proof of authorship or truth. A CID does not prove that a file is pinned or that the content is legally valid.

## Required safeguards before a release

- The `--use-node-profile` workflow shows all identity fields, original document text, and the current real Kubo Peer ID, then requires explicit confirmation before saving the local association and incorporating identity data.
- The `publish` workflow shows the complete package and requires explicit confirmation before network publication.
- Show the exact fields and complete document content that will be published.
- Preserve source document bytes and `.ots` proof files without silent modification.
- Keep application data outside the replaceable application-code directory.
- Test update preservation for identity profiles, source documents, proof files, generated packages, and local records.
- Never log complete identity records or document bodies unnecessarily.
- Do not claim encryption, selective disclosure, verified identity, or Bitcoin confirmation unless implemented and tested.

## Future encryption

Encryption is deliberately not implemented now. Future encryption should be introduced as a separately versioned storage/publication policy with explicit key management and migration tests, without changing the meaning of existing unencrypted records. It must not be retroactively claimed for records created before that feature exists.
