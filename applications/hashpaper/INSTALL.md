# HashPaper Installation

HashPaper is shipped as part of the Node Core OS application code and appears in the Applications menu. Selecting it opens the interactive HashPaper menu. A user-level launcher is installed automatically by the Node Core OS clean installer and updater at `~/.node-core/bin/hashpaper`. The companion script `installer/hashpaper-install.sh` can recreate that launcher and install/verify the OpenTimestamps client for an existing installation that already contains HashPaper. It does not download application code independently.

## Default local paths

The interactive menu does not ask users to type filesystem paths for normal local workflows. Original text/Markdown documents are stored in `~/.node-core/storage/`; package JSON files are stored in `~/.node-core/hashpaper/packages/`; publication receipts are stored in `~/.node-core/hashpaper/records/`. HashPaper uses the newest local text document by default and never overwrites an existing original or package. Explicit `--input`/`--output` arguments remain available for automation or importing an existing file.

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

HashPaper originals live in `~/.node-core/storage/`. Generated packages and publication receipts live outside the replaceable application-code directory:

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
