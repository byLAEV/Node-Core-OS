# HashPaper Installation

HashPaper is shipped as part of the Node Core OS application code and appears in the Applications menu. Selecting it opens the interactive HashPaper menu. A user-level launcher is installed automatically by the Node Core OS clean installer and updater at `~/.node-core/bin/hashpaper`. The companion script `installer/hashpaper-install.sh` can recreate that launcher and install/verify the OpenTimestamps client for an existing installation that already contains HashPaper. It does not download application code independently. The separate `installer/hashpaper-update.sh` updater downloads and updates only the HashPaper application code.

## Default local paths

HashPaper requires a fresh identity-data consent each time its interactive application is opened. The user must type `ACCEPT IDENTITY DATA USE` before the menu is shown. After consent, HashPaper reads the saved Node Core OS identity profile and live Kubo Peer ID; every new interactive Markdown original embeds those fields as plaintext. Consent is not saved as permanent consent. Timestamping submits the document hash to OpenTimestamps; publishing a copy through IPFS can disclose the full text and embedded identity publicly.

The installer creates a private, application-specific data tree at `~/.node-core/hashpaper/`: originals and their adjacent `.ots` files live in `documents/`, timestamp-enriched copies prepared for IPFS live in `ipfs/`, advanced JSON packages live in `packages/`, and publication receipts/history live in `records/`. This `ipfs/` directory is only HashPaper's local staging area for files; it is not an IPFS/Kubo repository. All applications use the Kubo executable, daemon, API, and repository configured and managed by Node Core OS (`ipfs_repo_path`), and HashPaper publishes through Node Core OS's shared `NodeRuntime`/`ContentManager` interfaces. HashPaper must not initialize, replace, or create a separate Kubo repository. New originals use the document title as the filename and are never overwritten. The document picker shows history in chronological order, 10 items per page, and reports whether each original has an `.ots` file. The text editor accepts multiline text; Enter adds a line, Ctrl-D finishes input, and Escape cancels. Creation is executed only after the application returns to the menu command selection flow.

The IPFS action creates a separate Markdown copy with original SHA-256, proof presence/fingerprint, and current OpenTimestamps status. It publishes the copy, verifies retrieval against the local bytes, confirms pin state, and saves a receipt with public gateway URLs. Gateway availability is not guaranteed. Existing files in the legacy `~/.node-core/storage/` directory are not deleted or automatically moved. Explicit `--input`/`--output` arguments remain available for advanced CLI use.

## Requirements

- A supported GNU/Linux terminal environment.
- Python 3.10 or newer.
- A functioning Node Core OS installation for identity association and Kubo/IPFS publication.
- The official `opentimestamps-client` package, installed automatically into the user-owned private environment at `~/.node-core/runtime/opentimestamps-venv/` by the Node Core OS installer/updater or HashPaper installer. No root access or system Python modification is required.

## Verification

From the repository root:

```bash
python3 -m unittest discover -s applications/hashpaper/tests -v
bash installer/tests/update-preservation.sh
bash installer/tests/hashpaper-install.sh
```

GitHub Actions additionally performs a clean installation and uninstall on Ubuntu 24.04 in two service modes. Its E2E test creates synthetic HashPaper data, publishes a package through the live Kubo daemon, retrieves it by CID and compares bytes, checks a real Kubo Peer ID association, and exercises uninstall safety checks.

## Data preservation

HashPaper originals live in `~/.node-core/hashpaper/documents/`. Generated packages and publication receipts live outside the replaceable application-code directory:

```text
~/.node-core/hashpaper/
├── packages/
└── records/
```

The updater preservation tests check these data categories through successful update and rollback scenarios, alongside Node Core OS configuration, local storage, and Kubo data.

## Limitations

- The companion installer recreates `~/.node-core/bin/hashpaper` and installs/verifies the OpenTimestamps CLI; it is not a standalone installer for a fresh machine and requires Node Core OS to be installed first.
- The Node Core OS updater downloads the current application source, installs/verifies the official OpenTimestamps CLI in the private user environment, compiles Node Core OS and HashPaper, runs the HashPaper unit tests before marking the new commit successful, and rolls back application code if verification fails. HashPaper resolves the executable directly from that private environment when it is not in `PATH`.
- Re-running the clean installer over an existing `app/` directory is refused; use `~/.node-core/bin/node-core-update` to update existing installations safely.
- Automated OpenTimestamps tests use a fake executable. Live calendar submission and successful Bitcoin attestation verification must not be inferred from those tests.
- Encryption is not implemented; the evidence package contains the complete original text and included identity fields in cleartext.
- Use synthetic data in tests and review the complete package before public IPFS publication.
