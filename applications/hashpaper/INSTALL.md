# HashPaper Installation

HashPaper is shipped as part of the Node Core OS application code and appears in the Applications menu. Selecting it opens the interactive HashPaper menu. There is no separate HashPaper installer yet.

## Requirements

- A supported GNU/Linux terminal environment.
- Python 3.10 or newer.
- A functioning Node Core OS installation for identity association and Kubo/IPFS publication.
- The official OpenTimestamps `ots` executable in `PATH` for timestamp operations.

## Verification

From the repository root:

```bash
python3 -m unittest discover -s applications/hashpaper/tests -v
bash installer/tests/update-preservation.sh
```

GitHub Actions additionally performs a clean installation and uninstall on Ubuntu 24.04 in two service modes. Its E2E test creates synthetic HashPaper data, publishes a package through the live Kubo daemon, retrieves it by CID and compares bytes, checks a real Kubo Peer ID association, and exercises uninstall safety checks.

## Data preservation

HashPaper data lives outside the replaceable application-code directory:

```text
~/.node-core/hashpaper/
├── documents/
├── proofs/
├── packages/
└── records/
```

The updater preservation tests check these data categories through successful update and rollback scenarios, alongside Node Core OS configuration, local storage, and Kubo data.

## Limitations

- A separate HashPaper installer is not implemented.
- Automated OpenTimestamps tests use a fake executable. Live calendar submission and successful Bitcoin attestation verification must not be inferred from those tests.
- Encryption is not implemented; the evidence package contains the complete original text and included identity fields in cleartext.
- Use synthetic data in tests and review the complete package before public IPFS publication.
