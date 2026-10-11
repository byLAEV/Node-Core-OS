# HashPaper for Node Core OS

HashPaper is an application included in the Node Core OS source tree. It creates local UTF-8 text/Markdown originals, calculates SHA-256 over the exact original bytes, requests timestamp operations through the official OpenTimestamps CLI, builds a transparent JSON evidence package, and publishes that package through the existing Node Core OS Kubo/IPFS content interfaces after explicit confirmation.

## Pending OpenTimestamps proof display\n\nHashPaper can display the original document SHA-256 and the SHA-256 fingerprint of the local `.ots` proof while the timestamp is pending. The proof-file fingerprint is a local integrity identifier for that exact `.ots` file; it is **not** an official OpenTimestamps-issued timestamp ID and it does not prove Bitcoin confirmation. The displayed state comes from running the official `ots verify` command against the original proof. A pending proof is labelled `WAITING_FOR_BITCOIN` and is not presented as verified.\n\nCLI usage:\n\n```bash\npython applications/hashpaper/main.py proof-info --input /path/to/document.md --report /path/to/proof-info.json\n```\n\n## Current verified milestone

The following components are implemented in the main branch:

- Local original-document creation with no-overwrite behavior.
- Transparent JSON packages that embed the complete original text and known identity/node fields.
- SHA-256 calculated from the exact original bytes, separately from the generated package hash.
- An adapter for the official `ots` CLI: `stamp`, `check`, and `upgrade`.\n- A proof-information view available as menu option 7 or `proof-info`, showing the original SHA-256, the local `.ots` file SHA-256 fingerprint, and the actual status returned by the official verifier.
- A Kubo/IPFS publisher using Node Core OS `ContentManager` and `KuboManager`. It asks for explicit confirmation, retrieves the published CID, compares the retrieved bytes, and checks pin state.
- An identity association flow that requires an existing Node Core OS identity profile, a live Kubo Peer ID, and explicit confirmation.
- A Node Core OS Applications-menu entry with an interactive HashPaper menu for creating documents, running timestamp operations, building packages, and publishing; installer checks for HashPaper files/compilation.
- Persistent HashPaper data directories outside the replaceable application-code tree.\n- A companion user-level installer at `installer/hashpaper-install.sh` that creates `~/.node-core/bin/hashpaper` for an existing Node Core OS installation without replacing application files or user data.
- Automated tests for the local application, timestamp adapter behavior, publication behavior, and data-preservation scenarios.

GitHub Actions has passed the Linux terminal CI and the Ubuntu 24.04 installer E2E workflow. The E2E run includes a clean install in both service modes, publication/retrieval against a live Kubo daemon, identity association against the live Kubo Peer ID, and uninstall safety checks. See the repository Actions page for the exact run and commit.

## Interactive menu and commands

Launching HashPaper from the Node Core OS Applications menu now opens an interactive menu. It supports local document creation, OpenTimestamps submission/check/upgrade, transparent package generation, and IPFS publication. The menu prompts for required paths and fields, and the identity/publication workflows retain their explicit confirmation steps. The CLI commands below are also available for scripted workflows.


Run from the repository root on GNU/Linux with Python 3.10 or newer:

```bash
python3 -m unittest discover -s applications/hashpaper/tests -v

python3 applications/hashpaper/main.py create \
  --output /tmp/document-001.md \
  --title "Synthetic test" \
  --text "Synthetic body"

python3 applications/hashpaper/main.py stamp \
  --input /tmp/document-001.md \
  --report /tmp/document-001.stamp-report.json

python3 applications/hashpaper/main.py check \
  --input /tmp/document-001.md \
  --report /tmp/document-001.check-report.json

python3 applications/hashpaper/main.py upgrade \
  --input /tmp/document-001.md \
  --report /tmp/document-001.upgrade-report.json

python3 applications/hashpaper/main.py package \
  --input /tmp/document-001.md \
  --output /tmp/document-001.ipfs.json \
  --ots-json /tmp/document-001.check-report.json

# Optional identity association: review and confirm the complete fields.
python3 applications/hashpaper/main.py package \
  --input /tmp/document-001.md \
  --output /tmp/document-001.with-identity.json \
  --use-node-profile

# Public disclosure: review the complete package and type PUBLISH.
python3 applications/hashpaper/main.py publish \
  --input /tmp/document-001.ipfs.json \
  --report /tmp/document-001.publication.json
```

Timestamp commands require the official `ots` executable in `PATH`. A successful submission is not proof that a Bitcoin attestation is already available. After an upgrade, run `check` to verify the proof against the unchanged original. The adapter retains a backup when the proof changes, including when an upgrade is interrupted.

## Live OpenTimestamps test

To test the real OpenTimestamps client without using personal data, open the repository's Actions tab and run **HashPaper — Live OpenTimestamps Validation** manually. After this workflow is merged into the default branch, it is also scheduled weekly on Sunday at 06:00 UTC. The workflow installs the official client, creates a synthetic document, submits it, checks the proof, verifies that the original SHA-256 is unchanged, and uploads the synthetic proof/report artifacts for seven days. A pending Bitcoin attestation is not considered a verified timestamp. The live workflow accepts only `VERIFIED` or `WAITING_FOR_BITCOIN` from the official check; network errors, malformed proofs, and inconclusive states fail the workflow while preserving diagnostic artifacts.

## Persistent data

Node Core OS creates these directories under `~/.node-core/hashpaper/`:

- `documents/` — original documents.
- `proofs/` — OpenTimestamps proof files.
- `packages/` — generated packages.
- `records/` — local publication receipts and records.

They are outside the replaceable application-code directory so a normal application update does not remove user data.

## Transparency and security

**Encryption is NOT IMPLEMENTED.** A generated package intentionally contains the complete original document text and any identity fields included in the package, in cleartext. Publishing the package to IPFS can expose that information to third parties. Use synthetic data for testing and do not publish real identity or civil-document data unless public disclosure is intentional.

A profile marked `declared` is not independently verified civil identity. A Kubo Peer ID identifies a technical node, not the person controlling it. An OpenTimestamps proof does not by itself establish authorship, truth, ownership, or civil identity. A CID identifies exact content; it does not alone prove validity, pinning, or permanent availability.

HashPaper is shipped with the main Node Core OS code tree. A separate HashPaper installer has not yet been implemented. A manual GitHub Actions workflow, `.github/workflows/hashpaper-opentimestamps-live.yml`, is available for live testing with synthetic data. It is intentionally opt-in because it requires external network access; an immediate pending result is not reported as Bitcoin verification.


## Independent HashPaper updates

Existing Node Core OS installations can update HashPaper without reinstalling or replacing the Node Core OS core. Download the standalone updater from the repository and run it as the normal Termux/Linux user:

```bash
mkdir -p "$HOME/.node-core/bin"
curl --fail --location --show-error \
  https://raw.githubusercontent.com/byLAEV/Node-Core-OS/main/installer/hashpaper-update.sh \
  --output "$HOME/.node-core/bin/hashpaper-update"
chmod 700 "$HOME/.node-core/bin/hashpaper-update"
"$HOME/.node-core/bin/hashpaper-update"
```

The updater requires an existing Node Core OS installation. It updates only `app/applications/hashpaper/`, verifies the downloaded code with Python compilation and HashPaper unit tests, asks before replacing files, and attempts rollback if post-update verification fails. Persistent HashPaper data under `~/.node-core/hashpaper/`, identity, configuration, local storage, and Kubo/IPFS data remain outside the update target. Do not run it as root.

