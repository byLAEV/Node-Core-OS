# HashPaper for Node Core OS — Functional Manifest and Audit Guide

- **Document type:** normative functional manifest, operator manual, and code-audit guide.
- **Application:** HashPaper for Node Core OS.
- **Code root:** `applications/hashpaper/`.
- **Primary entry points:** `applications/hashpaper/main.py`, `applications/hashpaper/hashpaper/cli.py`.
- **Related components:** `documents.py`, `timestamp.py`, `publication.py`, `identity.py`, Node Core OS `NodeConfig`, `NodeRuntime`, `ContentManager`, and `KuboManager`.
- **Audience:** operators, developers, code reviewers, security reviewers, test authors, and auditors.
- **Status rule:** this document specifies expected behavior and points to implementation; a statement is not evidence that a behavior passed a test. The cited code and automated/runtime test results determine conformance.
- **Scope:** this manifest describes the HashPaper implementation in this repository revision. Re-check paths, menu text, defaults, and test results whenever code changes.

## 1. Purpose and conformance model

HashPaper creates local UTF-8 text/Markdown originals, calculates SHA-256 over exact original bytes, delegates timestamp operations to the official OpenTimestamps `ots` command-line client, builds transparent JSON evidence packages, and can publish selected packages through Node Core OS Kubo/IPFS integration after explicit user confirmation.

The manifest is intended to make the application auditable in four linked layers:

1. **Declared behavior:** what the menu/command is supposed to do.
2. **Implementation:** the source file and function that implement it.
3. **Observable result:** files, JSON fields, terminal messages, exit codes, and network actions that can be inspected.
4. **Verification:** automated tests and manual steps that establish whether implementation matches the declaration.

A feature is **conformant** only when implementation and tests support the declared behavior. If a test has not been run, the result must be marked **not verified**, not assumed successful.

### Normative language

- **MUST**: required behavior; a deviation is a defect.
- **MUST NOT**: prohibited behavior.
- **SHOULD**: expected default unless a documented reason justifies an exception.
- **MAY**: optional behavior.

## 2. Source map and responsibilities

| Source path | Responsibility | Audit focus |
|---|---|---|
| `applications/hashpaper/main.py` | Application entry point | Argument forwarding, startup errors, executable behavior |
| `applications/hashpaper/hashpaper/cli.py` | CLI parser, interactive menu, paths, user confirmations, command orchestration | Menu-to-command mapping, default path selection, consent, exception handling |
| `applications/hashpaper/hashpaper/documents.py` | Original document and transparent package construction/writes | Exact bytes, UTF-8, SHA-256, no-overwrite guarantees, package schema |
| `applications/hashpaper/hashpaper/timestamp.py` | Adapter around official `ots` CLI | Argument list, proof lifecycle, statuses, backups, hashes, timeout/errors |
| `applications/hashpaper/hashpaper/publication.py` | Kubo/IPFS package publication | Explicit authorization, CID, retrieval byte comparison, pin state, receipt |
| `applications/hashpaper/hashpaper/identity.py` | Node Core OS identity profile and Peer ID integration | Missing values, consent, association semantics, profile writes |
| `node_core/config.py` | Node Core OS data/config paths | Effective `NODE_CORE_DATA_DIR`, local storage path |
| `node_core/runtime.py` and Node Core OS content/IPFS modules | Runtime, content manager, Kubo daemon/API | Daemon/API availability, repository location, resource lifecycle |
| `applications/hashpaper/tests/` | HashPaper unit/regression tests | Expected contracts and mocked external commands |
| `.github/workflows/` | CI and installer integration checks | Clean install, version assertions, test execution, workflow results |

Auditors SHOULD read the actual function implementation and its tests before accepting a behavior. A README description alone is not sufficient evidence.

## 3. Storage layout and path resolution

### 3.1 Root directory

The default Node Core OS data root is `~/.node-core/`. When `NODE_CORE_DATA_DIR` is set, path resolution MUST respect that override where the component supports it. The effective configuration is defined by `node_core/config.py` and consumed by HashPaper's `_data_dir()` / `_documents_dir()`.

HashPaper's canonical directory for new timestampable originals is the configured local-storage root plus `opentimestamps/`. In the standard configuration this is expected to be:

```text
~/.node-core/
├── storage/
│   └── opentimestamps/
│       ├── Genesis-HashPaper.md
│       └── Genesis-HashPaper.md.ots
└── hashpaper/
    ├── documents/       # legacy original documents, read in place
    ├── ipfs/            # HashPaper-specific IPFS-related local artifacts, if used
    ├── packages/        # transparent JSON packages
    └── records/         # publication receipts/reports
```

Do not assume every directory is created at installation time; some are created lazily by the function that needs them.

### 3.2 Path behavior

- `_expanded_path()` expands environment variables and `~`.
- `_data_dir()` reads `NODE_CORE_DATA_DIR`, otherwise defaults to `Path.home() / ".node-core"`.
- `_documents_dir()` uses `NodeConfig.load().local_storage_path / "opentimestamps"`; if Node Core's config module cannot be imported, standalone mode falls back to `_data_dir() / "storage" / "opentimestamps"`.
- `_legacy_documents_dir()` identifies the former `hashpaper/documents` location.
- `_document_directories()` searches the canonical and legacy locations without automatically moving files.
- Package defaults use `hashpaper/packages/`; publication reports use `hashpaper/records/`.

**Required invariants**
1. New originals are created in the canonical directory unless the caller supplies an explicit output path.
2. Existing originals and `.ots` files MUST NOT be silently moved or deleted by path migration.
3. History and default document selection MUST retain access to legacy originals.
4. Path overrides must be tested with a temporary `NODE_CORE_DATA_DIR`; tests must not write into the developer's real home directory.
5. The program MUST NOT silently overwrite an existing original, package, or publication receipt when choosing a default output name.

### 3.3 Default names and collision handling

The interactive/CLI default original starts at `Genesis-HashPaper.md`. If occupied, the path selector searches numbered alternatives such as `Genesis-HashPaper-2.md`. The package and publication-report selectors use equivalent numbered names in their respective directories.

The source of truth for exact behavior is `_default_document_path()`, `_default_package_path()`, and `_default_publication_report_path()`. Auditors SHOULD test the empty directory, one occupied name, multiple occupied names, an explicit output path, and a legacy-only document history.

## 4. Application entry and authorization

### 4.1 Interactive menu startup

The interactive menu calls `_authorize_identity_session()` before entering the menu loop. The current implementation requires the exact phrase `ACCEPT IDENTITY DATA USE`. This is a per-session decision, not persistent consent.

The consent text states that:
- the saved Node Core OS identity profile and live Kubo Peer ID will be read;
- newly created Markdown originals can include identity fields and a node identifier;
- those fields are plaintext;
- OpenTimestamps timestamps the document hash, not the complete text;
- IPFS publication can expose the package to third parties.

After acceptance, the code boots `NodeRuntime`, loads the identity and live Peer ID, and performs the identity association flow. If the profile/Peer ID/runtime cannot be loaded, the interactive session fails closed and reports an error.

**Audit warning:** consent is a control over the interactive startup path. Do not assume it protects every direct CLI subcommand; inspect each CLI command's own confirmation and identity-handling path separately.

### 4.2 Privacy and disclosure requirements

- HashPaper's transparent JSON package includes the full original text and any selected identity/node fields in cleartext.
- Encryption is **NOT IMPLEMENTED**.
- An IPFS CID identifies content; it does not make the content private.
- A Kubo Peer ID is a technical node identifier, not proof of civil identity or legal control.
- A profile marked `declared` is not independently verified civil identity.
- A hash/timestamp alone does not prove authorship, truth, ownership, or identity.
- The application MUST show an explicit disclosure warning and require the documented confirmation before publishing.
- Test real personal information only in a controlled environment; use synthetic data for CI.

## 5. Interactive menu contract

The interactive menu in `cli.py` currently declares the following choices. Confirm the current source before using this table as an operational checklist for a different revision.

### Option 1 — Create original document

**Intent:** create a new local UTF-8 Markdown original, with the session's accepted identity/node fields where the interactive flow requires them.

**Expected steps**
1. The user selects option 1.
2. HashPaper requests a title and document body.
3. The body editor accepts multiline text in a TTY; Enter inserts a newline, Ctrl-D finishes, and ESC cancels. Non-interactive input uses a one-line fallback.
4. HashPaper rejects cancelled/empty input and disallowed terminal-control characters.
5. It selects the next free canonical output path.
6. The document writer creates the original without overwriting an existing file.
7. The application displays the resulting path and metadata, including SHA-256 and size.

**Expected observable result:** one new original file at the chosen path and a metadata result with the exact-byte SHA-256 and size. Timestamp submission and IPFS publication are separate operations; creating a document MUST NOT itself imply either operation succeeded.

**Audit points:** `_read_multiline_body()`, `_default_document_path(for_create=True)`, `write_original()`, option-1 branch of the menu, and tests for cancellation, control characters, identity inclusion, and no-overwrite behavior.

### Option 2 — Send selected document to OpenTimestamps

**Intent:** submit the exact original file to the official OpenTimestamps client, or inspect an existing proof without submitting a duplicate.

**Expected steps**
1. Select an eligible original from history or the default selector.
2. Confirm the selected path.
3. HashPaper checks that the original exists, is UTF-8 text/Markdown, and does not contain disallowed terminal-control characters.
4. The timestamp adapter checks for the adjacent `<original>.ots` path.
5. If no proof exists, it invokes the official client with an argument list equivalent to `ots stamp <original>`, then verifies the original bytes did not change and that a non-empty proof was produced.
6. If a non-empty proof already exists, it invokes verification against the original instead of resubmitting or overwriting that proof.
7. If the existing proof path is a directory/non-file or is empty, it raises an explicit error and preserves that path.
8. The result/report displays the document SHA-256, proof-file SHA-256 when available, status, verification state, captured client output, and any identifiers actually printed by the official client.

**Expected observable result:** for a newly submitted proof, usually `WAITING_FOR_BITCOIN` and `NOT_VERIFIED`; for an existing proof, operation `stamp-existing-proof` with the verifier's actual state. A successful submission is not the same as a Bitcoin-confirmed attestation.

**Audit points:** `OpenTimestampsClient.stamp()`, `OpenTimestampsClient.check()`, `_run()`, timestamp adapter tests. The `.ots` file is evidence data and MUST NOT be overwritten merely to repeat the request.

### Option 3 — Check an OpenTimestamps proof

**Intent:** ask the official client to verify an existing proof against its unchanged original.

**Expected steps**
1. Select an original with a non-empty adjacent `.ots` proof.
2. Invoke the adapter's verification operation (official CLI invocation equivalent to `ots verify <proof>`).
3. Capture stdout/stderr and the exit code.
4. Map the actual client output to a conservative state.
5. Confirm the original SHA-256 did not change.
6. Display/store a structured report.

**Expected statuses:** `VERIFIED` only when the official client returns a successful Bitcoin block attestation; `WAITING_FOR_BITCOIN` when the client explicitly reports pending confirmation; network failures, proof errors, and inconclusive output remain distinct non-verified states.

**Audit points:** status parser and `check()`; tests for verified, pending, network error, malformed/missing proof, unchanged original, and conservative identifier parsing.

### Option 4 — Upgrade an OpenTimestamps proof

**Intent:** ask the official client to advance a pending proof when calendar/attestation data is available.

**Expected steps**
1. Select an original with a usable proof.
2. The adapter creates a unique `.before-upgrade` backup before mutation.
3. Invoke the official upgrade command on the proof.
4. Keep the backup if proof bytes change; remove a redundant backup only when the current proof is byte-identical to it.
5. Report the outcome without equating “timestamp complete” with successful verification against the original.
6. Run option 3/check after upgrade to verify the updated proof.

**Expected observable result:** a report with upgrade status and proof fingerprints; when the proof changes, the prior bytes remain recoverable in the backup. The user should run Check after Upgrade.

**Audit points:** `check(original, upgrade=True)`, backup naming, interrupted-command handling, byte comparisons, and tests for success, no change, changed proof, and exception/timeout.

### Option 5 — Publish a timestamp-indicator copy to IPFS

**Intent:** make and publish a separate Markdown copy with timestamp indicators; do not silently alter the original.

**Expected steps**
1. Select an original.
2. Display whether its adjacent proof is present and non-empty.
3. Explain that a separate copy will be created and published.
4. Ask for the explicit publication confirmation.
5. Build the copy/package through the publication implementation and Node Core OS content/Kubo interfaces.
6. Retrieve the published content by CID, compare bytes against the local content, and inspect pin state.
7. Display the receipt and public gateway URLs, noting that gateway availability is not guaranteed.

**Expected observable result:** a publication receipt containing the CID and observed publication/pin/retrieval results. If the user cancels, HashPaper MUST NOT submit the content to Kubo.

**Audit points:** menu option-5 branch, publication helper, `HashPaperPublisher.publish_package()`, content manager/Kubo manager, and mocked/live integration tests. Verify which exact artifact is published and where its local copy/receipt is written.

### Option 6 — IPFS publication history and gateways

**Intent:** inspect local publication records and show the recorded CIDs/gateway links.

**Expected observable result:** entries sourced from local records, including original/package path, CID, observed pin state, and gateway links where available. A displayed gateway URL is a retrieval route, not a guarantee that the gateway is online or that the data is permanently pinned.

**Audit points:** history-reading function and `hashpaper/records/`; test empty history, valid records, malformed records, and missing gateway configuration.

### Option 7 — Show .ots hashes and processing status

**Intent:** display evidence fingerprints and the official client's current interpretation of the timestamp proof.

**Expected steps**
1. Select an original/proof pair.
2. Calculate SHA-256 of the exact original bytes.
3. Calculate SHA-256 of the exact non-empty `.ots` bytes when present.
4. Run the official verifier for an existing proof.
5. Display the status and verification state; do not infer hidden identifiers.

**Expected observable result:** original hash, local proof fingerprint if present, and a conservative status such as not submitted, pending, verified, network error, or proof error. The local proof fingerprint is not an OpenTimestamps-issued timestamp ID.

**Audit points:** menu option-7 branch, `proof-info` command, `_sha256()`, `check()`, and proof-info tests.

### Option 8 — Build transparent JSON package (advanced)

**Intent:** build a local JSON evidence package for an existing original.

**Expected steps**
1. Select an existing original and output package path.
2. Optionally load an identity JSON or request use of the saved Node Core OS profile; those options are mutually exclusive.
3. Optionally include a report from an actual OpenTimestamps operation.
4. If using the Node Core profile, display the full original text, identity fields, current Peer ID, and previous association before writing.
5. Require the exact confirmation `INCLUDE IDENTITY AND NODE` before including/associating identity data.
6. Build a transparent package with the original text, exact-byte SHA-256, size, and only metadata actually available.
7. Write the package to a separate local file; do not publish it as a side effect.

**Expected observable result:** a local JSON package with a separate package hash/identity from the original document hash. The command warns that the original text and identity fields are cleartext. Publication remains a separate explicit action.

**Audit points:** `build_transparent_package()`, `write_package()`, `--identity-json`, `--use-node-profile`, `--ots-json`, and tests for schema, hashes, missing identity fields, confirmation/cancellation, and no accidental publication.

### Option 9 — Publish an existing transparent package (advanced)

**Intent:** publish an already-built JSON package after an explicit public-disclosure review.

**Expected steps**
1. Select an existing package.
2. Read and validate the package as a JSON object.
3. Display a warning that the complete package may be readable by third parties and that encryption is not implemented.
4. Display the exact package content for review.
5. Perform no network operation until the user types exactly `PUBLISH`.
6. Initialize/use Node Core OS runtime and publish through the Kubo/IPFS content interface.
7. Retrieve by CID, compare bytes, inspect pin state, and write a separate receipt without overwriting existing receipts.

**Expected observable result:** after confirmation, a receipt records the CID and publication checks. On cancellation, no content is sent by this HashPaper command. A CID is content-addressed; embedding the package's own CID into its own bytes would change the package and CID, so the receipt is separate.

**Audit points:** `publish` command in `main()`, package parsing, exact confirmation, `HashPaperPublisher`, retrieval byte comparison, pin-state check, and publication tests.

### Option 0 — Exit

Closes the interactive menu without initiating a new operation. Ctrl-C/EOF should be handled without corrupting an original or proof. Audit that cleanup/error handling leaves persistent artifacts intact.

## 6. Command-line interface contract

The CLI parser is implemented in `build_parser()`. Commands available in the current source include:

| Command | Required/important arguments | Intended effect |
|---|---|---|
| `create` | `--title`, `--text`; optional `--output` | Write a new local original |
| `stamp` | optional `--input`, `--report` | Submit a new proof, or verify a non-empty existing proof without resubmission |
| `check` | optional `--input`, `--report` | Verify an existing proof |
| `upgrade` | optional `--input`, `--report` | Upgrade a proof while preserving changed prior evidence |
| `proof-info` | optional `--input`, `--report` | Show hashes and status |
| `package` | optional `--input`, `--output`, identity/OTS options | Write a transparent local JSON package |
| `publish` | optional `--input`, `--report` | Publish an existing package after exact confirmation |

Run `python applications/hashpaper/main.py --help` to inspect current parser-level help. For every command, audit: path resolution, validation, exact external subprocess arguments, stdout/stderr capture, exit code, report schema, file write mode, cancellation behavior, and return code.

Example local-only workflow with synthetic data:

```bash
python3 applications/hashpaper/main.py create \
  --output /tmp/hashpaper-audit-example.md \
  --title "Synthetic audit example" \
  --text "Non-sensitive test content"

python3 applications/hashpaper/main.py stamp \
  --input /tmp/hashpaper-audit-example.md \
  --report /tmp/hashpaper-audit-example.stamp-report.json

python3 applications/hashpaper/main.py check \
  --input /tmp/hashpaper-audit-example.md \
  --report /tmp/hashpaper-audit-example.check-report.json
```

Use synthetic content. The example creates local files and calls the real OpenTimestamps client when stamp/check is executed; it is not a fully offline test. To avoid external calls, run the automated tests that use a fake `ots` executable.

## 7. OpenTimestamps adapter contract

The adapter MUST use the official CLI rather than inventing its own timestamp format. It MUST use an argument array, not shell string interpolation. It captures standard output and standard error, applies a timeout, and reports subprocess errors as `TimestampError`.

### 7.1 Submission

- Input original MUST exist, be a regular file, and not have a name ending in `.ots`.
- Text workflows require UTF-8 and reject disallowed terminal-control characters.
- Compute SHA-256 before submission and again after; if it changed, report an error.
- If no proof exists, invoke the official stamp operation and require a non-empty proof file afterward.
- If a non-empty proof already exists, run verification instead of resubmission and return operation `stamp-existing-proof`.
- An empty or non-file proof path MUST be preserved and reported as an explicit error.
- Do not claim Bitcoin confirmation merely because the stamp command returned zero or created a proof file.

### 7.2 Verification and status mapping

- `VERIFIED` is permitted only when the official verifier reports a successful Bitcoin block attestation.
- `WAITING_FOR_BITCOIN` is used only when the official output explicitly reports pending confirmation.
- Network failures, malformed/missing proofs, and ambiguous output MUST remain non-verified.
- `upgrade` completion alone is not verification; run `check` afterward.
- Report block height, calendar URLs, and transaction IDs only when explicitly available in the official client's output.
- Local `proof_sha256` is a fingerprint of exact local proof bytes, not an official timestamp identifier.

### 7.3 Evidence preservation

The original document is read-only for timestamp operations. When upgrading, create a unique backup before mutation. Retain changed prior proof bytes. Never overwrite an existing proof by calling stamp again. Tests MUST assert byte-for-byte preservation, not only path existence.

## 8. JSON evidence and report expectations

Audit the actual dataclasses and serializers in `documents.py`, `timestamp.py`, `publication.py`, and `cli.py`. Expected fields may include:

- **Original metadata:** resolved path, SHA-256 of exact original bytes, byte length.
- **Timestamp report:** operation, status, proof path, proof verification, original SHA-256, process return code, stdout/stderr, proof SHA-256, and only explicitly observed calendar URLs/transaction IDs/block height.
- **Package:** original content and original hash, included node/identity fields when provided, timestamp report fields when supplied, and package schema/version metadata.
- **Publication receipt:** source/package path, CID, retrieval byte comparison, observed pin state, and gateway information.

Do not assume field names or optionality from this summary alone: compare the actual schema and test assertions. Report files MUST be UTF-8 JSON objects where the command promises an object. Failed operations must not be represented as successful receipts.

## 9. Failure handling and recovery

| Failure | Required behavior | Operator action |
|---|---|---|
| User cancels text input | Do not create an original | Re-enter option if desired |
| Output path already exists | Do not overwrite it | Choose another output path |
| Original missing/unreadable/non-UTF-8 | Return explicit error; no stamp | Select or recreate a valid original |
| Existing `.ots` is empty/non-file | Preserve it and report error | Inspect the path; repair only with a deliberate recovery procedure |
| Existing non-empty proof is pending | Verify existing proof; do not resubmit | Run Check later; pending can be normal |
| OTS client missing/times out | Return explicit adapter error | Install/repair the official client in the normal user's environment; inspect logs/output |
| Proof malformed or verifier fails | Non-verified status/error | Preserve evidence; inspect original, proof, and captured output |
| IPFS/Kubo API unavailable | Fail publication; do not issue a false success receipt | Check daemon process, configured repository, API endpoint, and daemon logs |
| User declines `PUBLISH` | No publication request | Review package and consent only if publication is intended |
| Retrieval bytes differ from local package | Do not report successful content verification | Preserve CID/output and investigate |
| Pin check fails | Report actual pin state, not permanent availability | Inspect Kubo and pin result |
| Identity profile or Peer ID unavailable | Fail closed for the identity-association flow | Repair profile/runtime or use a non-identity flow only if supported |

## 10. Automated audit matrix

Test names and exact file paths can change. Locate tests with a repository search and verify the current assertions before treating a row as covered.

| Audit ID | Requirement | Minimum test evidence |
|---|---|---|
| HP-MAN-001 | New document uses canonical configured storage | Set temporary `NODE_CORE_DATA_DIR`; assert exact path |
| HP-MAN-002 | Legacy originals remain discoverable | Seed canonical and legacy paths; assert both appear |
| HP-MAN-003 | No overwrite of original/package/receipt | Pre-create destination; assert bytes unchanged and explicit error/alternate path |
| HP-MAN-004 | Original hash is exact-byte SHA-256 | Compare against independent `hashlib.sha256(path.read_bytes())` |
| HP-MAN-005 | Existing proof is verified, not restamped | Fake client records verify invocation; assert no stamp invocation |
| HP-MAN-006 | Existing proof bytes are preserved | Snapshot bytes before call; assert exact equality afterward |
| HP-MAN-007 | Empty/non-file proof path is preserved and rejected | Assert explicit error and path/content remains |
| HP-MAN-008 | Pending is not called verified | Fake official output indicates pending; assert pending state |
| HP-MAN-009 | Verified requires explicit block-attestation output | Positive and near-miss parser cases |
| HP-MAN-010 | Upgrade keeps previous proof if changed | Assert backup bytes equal prior proof |
| HP-MAN-011 | Identity inclusion requires consent and uses real available values | Cancellation and accepted-flow tests with synthetic profile |
| HP-MAN-012 | Publication requires exact confirmation | Decline path asserts publisher/network method was not called |
| HP-MAN-013 | Publication verifies retrieved bytes and pin state | Mocked unit test plus live Kubo integration test |
| HP-MAN-014 | JSON reports do not invent identifiers | Missing/unlabelled hashes yield empty/unavailable fields |
| HP-MAN-015 | Failures return nonzero/explicit error as contracted | CLI exit-code and report assertions |
| HP-MAN-016 | Install/update preserves user data | Installer/update E2E with seeded persistent files |
| HP-MAN-017 | Menu choice maps to intended handler | Unit test for each menu option and cancellation |
| HP-MAN-018 | Help/documentation matches parser | Compare `--help`, menu labels, and documented arguments |

Suggested Linux test command from repository root:

```bash
python3 -m unittest discover -s applications/hashpaper/tests -v
```

Run the repository's current Node Core OS and installer workflows as well. A local unit-test pass does not replace installer E2E or a live Kubo/OpenTimestamps test. Do not claim those passed unless the corresponding run is green on the commit under review.

## 11. Manual operator checklist

For a controlled synthetic-data test:

1. Record the commit SHA and effective `NODE_CORE_DATA_DIR`.
2. Confirm the configured storage paths without using root.
3. Open HashPaper and read the identity-data warning.
4. Decline consent once and confirm the session exits without creating/publishing data.
5. Re-open with synthetic test identity data and the exact consent phrase.
6. Create a short synthetic Markdown original; record path, size, and SHA-256.
7. Confirm a second create operation chooses a different path rather than overwriting.
8. Run stamp once; record status and the adjacent `.ots` hash if produced.
9. Run stamp again; confirm operation is `stamp-existing-proof`, the existing proof bytes are unchanged, and no second submission occurs.
10. If the result is pending, confirm it is not described as verified.
11. Run check; compare the displayed original hash to the original file bytes.
12. If performing upgrade, retain and inspect the prior-proof backup, then run check afterward.
13. Build a package and inspect its entire JSON, original hash, and privacy warning.
14. Cancel publication and verify that no publish method was invoked.
15. If testing live publication, use only synthetic content, type the exact confirmation, and check CID retrieval bytes and pin state.
16. Inspect local records, logs, and generated files.
17. Run the automated suite and installer E2E; capture links to the exact workflow run and commit.
18. Record deviations as audit findings with ID, reproduction, expected behavior, actual behavior, impact, source line, test, fix, and retest result.

## 12. Security boundaries and non-goals

HashPaper MUST NOT imply any of the following unless a separate mechanism proves it:

- Encryption or confidentiality of package content.
- Civil identity verification based only on a local profile.
- Authorship, truth, ownership, or legal validity based only on a hash or timestamp.
- Bitcoin confirmation based only on the presence of an `.ots` file.
- Permanent IPFS availability based only on a CID or one pin response.
- A network publication having occurred when the user cancelled.

The tool should preserve evidence and report uncertainty explicitly rather than manufacture certainty.

## 13. Experimental example: cryptographic identifiers for process descriptions

**Purpose:** demonstrate how a content hash can identify a specific process description in this manifest. This is a documentation and user-education experiment only. It does not add runtime behavior, execute steps, sign requests, or change HashPaper's internal request handling.

### 13.1 Rules for this example

1. Each identifier below is the SHA-256 digest of the exact UTF-8 bytes of the English description shown in the table.
2. For reproducibility, hash only the description text in the table cell: no quotation marks, no identifier, no table separators, and no trailing newline.
3. The `HP-DESC-NNN` value is a human-readable logical index. It is not the cryptographic hash.
4. The `sha256:` value identifies the exact description text. It does not, by itself, encode the item's order, meaning, author, or execution result.
5. The process order is defined separately by the sequence number and the `next` reference. The sequence is documentary and does not prove that the application actually executed these steps.
6. If a description changes, its SHA-256 must be recalculated and any references to the old hash must be reviewed. Do not silently reuse an old hash for changed text.

### 13.2 Worked example

This illustrative flow describes creating a local HashPaper document. The descriptions are intended to align with the current documented behavior; before using them as conformance evidence, compare each statement with the source and tests cited elsewhere in this manifest.

| Sequence | Logical index | SHA-256 identifier of exact description text | Description | Next logical index |
|---:|---|---|---|---|
| 1 | `HP-DESC-001` | `sha256:f5a3b3e2c7f34a2777a517b5af201edd40b5ce500ea2df9c43e0f72bb0ef00c6` | Receive a user request to create a local HashPaper document. | `HP-DESC-002` |
| 2 | `HP-DESC-002` | `sha256:41833b6c8d93ac49773045305de7c979548db39c4057efe180e7e2eb8be2bce4` | Validate the document title and body before writing. | `HP-DESC-003` |
| 3 | `HP-DESC-003` | `sha256:7a1c4c654ce9c79a1b5037134a01146de7389ab3edadc0ddc77111698971dca5` | Write the original document to the configured local storage path without overwriting an existing file. | `HP-DESC-004` |
| 4 | `HP-DESC-004` | `sha256:4e6e65b3ebd18d7aa81707a3b0caf0de6844816dcd08f90b773648401357a31b` | Calculate SHA-256 over the exact bytes of the saved original document. | `HP-DESC-005` |
| 5 | `HP-DESC-005` | `sha256:391d6b0bc0fce701273012c2282564a16b543ac1623e1d45c95f02404ca563b8` | Report the resulting path and hash to the user; timestamping and publication remain separate operations. | `END` |

### 13.3 How to read the index

- Looking up `HP-DESC-003` tells the reader that sequence 3 describes writing the original document without overwriting an existing file.
- Comparing the calculated SHA-256 with the table value checks whether the description text is unchanged under the encoding and byte rules above.
- Following `next` from `HP-DESC-001` to `HP-DESC-005` reconstructs the documented sequence.
- `END` is a logical terminator, not a cryptographic identifier.

This is a simple indexed reference model, not yet a hash chain: the hash of each item covers its own description only, and the order is recorded separately. A future experiment could hash a canonical structured record that includes the sequence and previous record's hash, but that would be a distinct design and must define serialization, versioning, and verification rules first.

### 13.4 Validation checklist for the example

- [ ] Recalculate every digest from the exact description text using UTF-8 and no trailing newline.
- [ ] Confirm each logical index is unique.
- [ ] Confirm every `next` reference resolves to an existing index or `END`.
- [ ] Confirm sequence numbers are strictly increasing and there are no accidental loops.
- [ ] Check each description against the implementation and tests; mark unsupported claims as unverified or revise them.
- [ ] Change one description in a controlled copy and confirm its digest no longer matches the recorded value.
- [ ] Ask a reader unfamiliar with the example to resolve an index and explain its meaning and next step.
- [ ] Record the result as a documentation experiment. Do not describe it as a HashPaper runtime feature.

## 14. Change-control rule for this manifest

Every change to a menu label, command, file path, default, status mapping, confirmation phrase, output schema, or storage write MUST include:

1. An update to this manifest and any relevant user-facing guide.
2. A test that asserts the new behavior or proves the invariant remains true.
3. An update to the changelog when user-visible behavior or storage contracts change.
4. CI validation on the commit being reviewed.
5. A note distinguishing implemented behavior from behavior not yet verified in runtime.

If code and manifest disagree, do not silently choose whichever sounds correct: file an audit finding, identify the actual implementation, then either fix the code to meet the manifest or revise the manifest with an explicit design decision and tests.
