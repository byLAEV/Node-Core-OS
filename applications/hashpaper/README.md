# HashPaper for Node Core OS

HashPaper is an application prototype for creating transparent document records, timestamping the exact original document with OpenTimestamps, and publishing a complete evidence package through the Node Core OS Kubo/IPFS layer.

## Current status

This directory establishes the application contract and local document-package foundation. It is not yet an end-to-end release: the OpenTimestamps client integration, Kubo publication workflow, installer integration, update preservation, and full CI coverage remain pending implementation and verification.

## Transparency and security status

- No encryption is implemented in this stage.
- The planned IPFS package intentionally includes the complete original document text, the identity fields explicitly selected for the record, the original document's SHA-256, and real OpenTimestamps results when available.
- Publishing such a package makes its contents publicly retrievable by anyone able to access the IPFS content. Use synthetic data for tests. Do not publish real identity or civil-document data unless you explicitly accept permanent public disclosure.
- A local identity profile is declared data, not independently verified civil identity. A Kubo Peer ID identifies a technical node, not the person controlling it.
- An OpenTimestamps proof can establish timestamp-related evidence for bytes; it does not by itself prove authorship, truth, ownership, or civil identity.
- A CID identifies the exact published package. It does not itself prove timestamp validity, pinning, identity, or permanent availability.

## Planned files

A record will preserve three separate artifacts:

1. The immutable original text/Markdown file whose exact bytes are submitted to OpenTimestamps.
2. The `.ots` proof file returned by the official OpenTimestamps client, with status tracked separately from proof-file existence.
3. A versioned IPFS package that includes the entire original text plus identity/node metadata, SHA-256, and only the OpenTimestamps/Bitcoin fields actually returned and verified.

Changes to the original create a new document version. If timestamp or verification metadata changes, a new package version and CID are produced; the original and prior package are not silently overwritten.

## Persistent data

Application data must live outside the replaceable Node Core OS application-code directory. The planned default is `~/.node-core/hashpaper/`; this location must be confirmed against the shared installer/update contract before release.

## Development

The project officially supports GNU/Linux terminal environments and Python 3.10+.

```bash
python3 -m unittest discover -s applications/hashpaper/tests -v
```

The current milestone is a local-first foundation, an adapter for the official OpenTimestamps CLI, and an explicit identity/Peer ID association flow. The adapter is tested with a fake executable in CI; that does not prove that a real calendar request or Bitcoin verification has succeeded. Kubo/IPFS publication now has an adapter using Node Core OS's existing `ContentManager` and `KuboManager`. The `publish` command prints the complete package and requires typing `PUBLISH` before network operations. It verifies byte-for-byte retrieval and confirms pin state. This adapter is tested with fake runtime objects in CI; a live Kubo end-to-end run is still pending. Installer integration remains pending.

## Local commands

Run from the repository root on GNU/Linux with Python 3.10+:

```bash
python3 applications/hashpaper/main.py create --output /tmp/document-001.md --title "Synthetic test" --text "Synthetic body"
python3 applications/hashpaper/main.py stamp --input /tmp/document-001.md --report /tmp/document-001.ots-report.json
python3 applications/hashpaper/main.py check --input /tmp/document-001.md --report /tmp/document-001.check-report.json
python3 applications/hashpaper/main.py upgrade --input /tmp/document-001.md --report /tmp/document-001.upgrade-report.json
python3 applications/hashpaper/main.py package --input /tmp/document-001.md --output /tmp/document-001.ipfs.json --ots-json /tmp/document-001.check-report.json
# Or load the actual Node Core identity and live Kubo Peer ID with explicit confirmation:
python3 applications/hashpaper/main.py package --input /tmp/document-001.md --output /tmp/document-001.with-identity.json --use-node-profile
python3 applications/hashpaper/main.py publish --input /tmp/document-001.ipfs.json --report /tmp/document-001.publication.json
```

The timestamp commands require the official `ots` executable in `PATH`. `stamp` creates the proof using remote calendars; it does not mean the Bitcoin attestation is already confirmed. `upgrade` retains a `.before-upgrade` backup if the proof changes. Run `check` afterwards to verify the proof against the original. `publish` is the exception: after showing the complete package, it asks for the exact confirmation `PUBLISH`, then uses the existing Node Core Kubo/content interfaces. It refuses to report success unless the retrieved bytes match and the CID is confirmed pinned. The CID is recorded in a separate receipt because embedding a package's own CID in the package would change its content. Use synthetic content for network tests.
