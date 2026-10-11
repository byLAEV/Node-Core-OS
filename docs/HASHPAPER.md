# HashPaper for Node Core OS

## Purpose

HashPaper is the document-evidence application planned for Node Core OS. It is designed to keep a local original, create an OpenTimestamps proof for the exact original bytes, assemble a transparent evidence package, and publish that package through the existing Kubo/IPFS content layer after end-to-end verification.

## Current implementation status

The first source-tree milestone is `applications/hashpaper/` version `0.1.0`. It provides local UTF-8 document creation, SHA-256 calculation, and transparent JSON package generation with tests. The complete original text is embedded in the package. It does **not** yet submit or verify OpenTimestamps proofs, publish to Kubo/IPFS, integrate with the main menu, or participate in installer/update lifecycle. The official OpenTimestamps CLI adapter is now implemented for `stamp`, `check`, and `upgrade`. CI exercises it with a fake CLI executable, not live calendars or Bitcoin verification. Kubo/IPFS publication now has an adapter using the existing Node Core `ContentManager` and `KuboManager`. It requires explicit confirmation, retrieves the resulting CID, compares bytes, and checks pin state; unit tests use fake runtime objects, so a live Kubo end-to-end test remains pending. Main-menu integration and installer/update lifecycle remain pending and must not be represented as operational.

## Artifact contract

1. **Original document**: a UTF-8 text or Markdown file. Its exact bytes are hashed with SHA-256 and must not be overwritten in place. An edit creates a new document/version.
2. **OpenTimestamps proof**: the `.ots` file produced and updated by the official OpenTimestamps client. Proof-file existence is not proof verification. Pending, network failure, attestation available, and verification success are distinct states.
3. **IPFS package**: a versioned JSON or Markdown record containing the entire original text, transparent identity/node fields, original byte length and SHA-256, proof filename and real OTS status, and Bitcoin details only when actually available and verified. Unknown values remain `null` or explicit pending/not-checked states. The package hash is not the original document hash.

A package changes when timestamp metadata changes. Such changes create a new package version and CID rather than implying that an existing CID is mutable.

## Identity and node semantics

The existing Node Core OS profile schema includes `identity_id`, `full_name`, `alias`, `nationality`, `issuing_country`, `document_type`, `document_number`, `birth_date`, `height_cm`, `gender`, `identity_status`, `node_id`, `created_at`, and `updated_at`. HashPaper must not invent values for missing fields. The profile's current status `declared` is not civil-identity verification. A Kubo Peer ID is a technical node identifier and does not establish who controls it.

The `package --use-node-profile` flow now requires an existing local identity profile and a live Kubo Peer ID. It displays the complete original text and all known profile fields, requires the exact confirmation `INCLUDE IDENTITY AND NODE`, and only then persists the local association and creates the package. The user can cancel before association or publication. Public publication separately requires typing `PUBLISH` after reviewing the complete package.

## Transparency and encryption

No encryption is implemented in this stage. The planned published package intentionally contains the full original text and the selected identity fields in cleartext. Anyone able to retrieve the public IPFS content can read those fields. Use synthetic data in tests; real identity data must not be published accidentally. Future encryption requires a separately specified and tested policy and key-management model. Documentation for each relevant update must state explicitly whether encryption is implemented; for this milestone it is not.

## Integration plan

1. Complete and test the local record workflow and schema.
2. The CLI adapter invokes only the official OpenTimestamps client for `stamp`, `verify`, and `upgrade`; CI uses a fake executable to test state handling. Live calendar and Bitcoin verification still require integration tests. Never reimplement its cryptographic protocol.
3. Distinguish pending proofs, network errors, available attestations, and successful verification.
4. Integrate with the existing `node_core.ipfs.KuboManager` and content registry only after confirming their current contracts. Do not expose Kubo's administrative RPC to applications.
5. The initial publisher adapter now retrieves the CID, compares bytes, and checks pin state. Add a live Kubo end-to-end test before release.
6. Add a HashPaper launcher/menu integration without weakening the Node Core OS application boundary.
7. Install application code under the replaceable code tree but keep all user documents, `.ots` files, packages, and application state outside it.
8. Update installer and updater with preservation tests for existing config, identity, local storage, Kubo repository, and HashPaper records.
9. Add CI coverage for local tests, mocked OTS outcomes, Kubo publication/retrieval, failure paths, clean install, and upgrade from a version without HashPaper.

## Release criteria

Do not declare a complete HashPaper release until OpenTimestamps and Kubo/IPFS workflows, installer/update integration, and relevant automated tests pass. The main installer currently has an evolving transaction model; HashPaper must not bypass it or cause application data to be deleted when the replaceable code directory is refreshed.
