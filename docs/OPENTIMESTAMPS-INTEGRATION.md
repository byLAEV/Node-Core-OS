# OpenTimestamps integration for Node Core OS

## Included client

HashPaper uses the official `opentimestamps-client` Python package in the private user environment:

`~/.node-core/runtime/opentimestamps-venv/`

The environment contains the `ots` command and the importable `opentimestamps` Python library. Node Core OS must not install these dependencies into system Python and must not run the installer as root.

Official projects:
- Client: https://github.com/opentimestamps/opentimestamps-client
- Python library: https://github.com/opentimestamps/python-opentimestamps
- Calendar server: https://github.com/opentimestamps/opentimestamps-server

## HashPaper workflow

1. Preserve the exact original document bytes.
2. Run the official `ots stamp` operation through HashPaper.
3. Store the resulting `.ots` proof under the user's persistent HashPaper proofs storage when the caller selected that path.
4. Run the official `ots verify` command against the original document and proof.
5. Use `ots upgrade` only to update the proof, then verify it again.
6. Report a pending proof as pending. A local proof-file SHA-256 is only a fingerprint of that file; it is not an OpenTimestamps-issued ID and does not prove Bitcoin confirmation.
7. Keep the original document unchanged; a proof must be verified against the exact bytes that were stamped.

Example from the repository root:

```bash
python3 applications/hashpaper/main.py stamp --input /tmp/synthetic-document.md --report /tmp/synthetic-document.stamp-report.json
python3 applications/hashpaper/main.py check --input /tmp/synthetic-document.md --report /tmp/synthetic-document.check-report.json
python3 applications/hashpaper/main.py upgrade --input /tmp/synthetic-document.md --report /tmp/synthetic-document.upgrade-report.json
```

These commands require a working `ots` command in PATH. In the installed application, use the private environment's bin directory. Never use personal documents for initial live tests.

## Optional calendar server

A calendar server is NOT required for the normal HashPaper client workflow. Public calendars can receive timestamp requests, and confirmation may take hours or longer.

An opt-in helper is available:

```bash
bash installer/opentimestamps-server-install.sh
```

It clones the official server repository into `~/.node-core/optional/opentimestamps-server` and installs its Python requirements into a separate user-owned virtual environment. It does not start the server, open ports, create a Bitcoin wallet, or fund anything.

Operating `otsd` is a separate infrastructure project. The official server requires a compatible Bitcoin Core node and a correctly configured wallet, calendar URI, donation address, and secret HMAC key. Do not expose the daemon directly to the public Internet. Read the upstream README and deployment guidance before configuring it. A test/regtest deployment is preferable for initial experiments.

The server source and requirements are maintained by the upstream project; Node Core OS does not fork or silently patch the consensus-critical implementation. Because the upstream server's dependency stack and Bitcoin Core requirements can change, a successful dependency installation is not proof that a production calendar is operational.

## Validation limits

Shell syntax and CI tests can validate installer behavior but cannot prove public-calendar availability, Bitcoin confirmation, or a real Termux device installation. A live test should use a synthetic document, verify that its original SHA-256 is unchanged, and distinguish `WAITING_FOR_BITCOIN` from a verified Bitcoin attestation.
