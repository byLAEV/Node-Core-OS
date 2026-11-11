# Termux ARM64 — physical-device acceptance checklist

**Status:** prepared; not yet executed on a physical Android device.  
**Target:** native Termux, Android ARM64 (aarch64).  
**Safety:** do not run as root. Never paste a real Bitcoin private key into ChatGPT, GitHub, CI logs, screenshots or support messages.

This checklist is the final device gate after GitHub Actions checks pass. Ubuntu CI cannot certify Android browser behavior, Termux process lifecycle, Android storage permissions or Termux:Widget integration.

## 1. Preflight — read-only

Run inside Termux:

~~~bash
printf 'PREFIX=%s\n' "$PREFIX"
printf 'TERMUX_VERSION=%s\n' "\${TERMUX_VERSION:-}"
uname -m
id
python --version
python -c 'import cryptography; print("cryptography", cryptography.__version__)'
command -v curl
command -v openssl && openssl version
df -h "$HOME"
pkg list-installed
~~~

Acceptance:
- PREFIX is /data/data/com.termux/files/usr.
- uname -m reports aarch64.
- UID is not 0.
- Python, cryptography, curl and Bash are available.
- Record whether OpenSSL CLI is available; the installer may use HTTP loopback fallback if TLS cannot start.

Do not run pkg upgrade as part of this acceptance test.

## 2. Lobby installation only

The bootstrap must install the Lobby independently and must not install or update Node Core OS:

~~~bash
pkg install curl python tar bash -y
curl -fsSL https://raw.githubusercontent.com/byLAEV/Node-Core-OS/feature/termux-local-lobby/compatibility/termux/bootstrap-lobby.sh -o "$HOME/bootstrap-lobby.sh"
bash "$HOME/bootstrap-lobby.sh"
~~~

Acceptance:
- Installer exits with status 0.
- ~/.node-core/lobby/server.py and ~/.shortcuts/node-core-lobby exist.
- Existing server.json, TLS certificate/key, logs and PID state are preserved on a subsequent Lobby reinstall.
- Lobby listens only on 127.0.0.1:8765.
- GET /health reports the actual transport. Do not mark HTTPS as passed unless HTTPS itself responds.

~~~bash
curl -kfsS https://127.0.0.1:8765/health || true
curl -fsS http://127.0.0.1:8765/health || true
ps -A | grep '[s]erver.py'
~~~

A browser warning for the self-signed local certificate is expected unless the certificate has been explicitly trusted. Encryption and browser trust are separate properties.

## 3. Lobby and Android lifecycle

- Open the Lobby from the local browser URL.
- Verify the home screen, status, diagnostics, report export and directory manifest.
- Open the Termux:Widget shortcut and confirm it launches/reopens the Lobby.
- Stop/restart the Lobby using the shortcut; confirm one server process remains and the PID file refers to that process.
- Put Termux in the background, lock the screen, and return after a short wait.
- Repeat with Android battery optimization enabled and disabled, recording observed behavior rather than assuming background execution is guaranteed.
- Verify no service binds to a non-loopback interface.

## 4. First Node Core OS installation and identity association

Perform only after CI and package checks have passed and the user is ready to install on this device.

- Confirm the Lobby detects that Node Core OS is not installed and offers the first-install path.
- Enter the declared name and Bitcoin HEX key only in the local device browser over the authenticated HTTPS loopback service. Never copy the key into a terminal command or diagnostic report.
- Confirm the displayed Bitcoin Mainnet P2WPKH address matches the locally expected address.
- Confirm the first-install server gate rejects execution when no valid proof is staged.
- Run the verified official installer package with explicit confirmation.
- Confirm the installer creates the persistent Ed25519 NODE ID under ~/.node-core/identity/.
- Confirm the Lobby associates the staged Bitcoin entity with that NODE ID and records the relationship in identity/entity-registry.json.
- If association fails, retry the association action; do not re-enter the Bitcoin key unless the local proof has expired or been explicitly cancelled.
- Confirm the declared-name assurance remains declared; NODE ID proof-of-possession is a separate cryptographic result.

Read-only identity inspection:

~~~bash
python - <<'PY'
from pathlib import Path
from node_core.identity.node_identity import NodeIdentityStore
from node_core.identity.entity_registry import EntityIdentityRegistry
root = Path.home() / ".node-core"
print("NODE ID:", NodeIdentityStore(root).load()["node_id"])
print("Entity count:", len(EntityIdentityRegistry(root).list_entities()))
PY
~~~

Run the inspection from the installed application's Python environment with its application path available, if the system Python cannot import Node Core OS modules.

## 5. Update and persistent-data preservation

Before updating, record the public NODE ID and file hashes. Do not print or copy private-key contents:

~~~bash
cd "$HOME/.node-core/app"
"$HOME/.node-core/runtime/node-core-venv/bin/python" - <<'PY'
from pathlib import Path
from node_core.identity.node_identity import NodeIdentityStore
root = Path.home() / ".node-core"
print("NODE ID before update:", NodeIdentityStore(root).load()["node_id"])
PY
sha256sum \
  "$HOME/.node-core/identity/node.json" \
  "$HOME/.node-core/identity/private/node.key" \
  "$HOME/.node-core/identity/entity-registry.json" \
  "$HOME/.node-core/lobby/bitcoin-identity-pending.json" \
  "$HOME/.node-core/ipfs/config"
ipfs version 2>/dev/null || "$PREFIX/bin/ipfs" version
~~~

If the installed Kubo executable is not on PATH, use the exact executable shown by the local Node Core OS configuration.

Then:
- Select the verified official update package in the Lobby.
- Confirm the update path does not request the Bitcoin private key again.
- Execute the official updater with explicit confirmation.
- Confirm the application version changes to the selected release.
- Re-run the NODE ID and SHA-256 checks above; all identity hashes and the public NODE ID must remain unchanged.
- Confirm a known user-created file under ~/.node-core/storage/ remains byte-identical.
- Confirm ~/.node-core/ipfs/config, the Kubo executable and the repository remain present.
- Confirm Kubo starts and its local API responds after the update.
- Confirm the Lobby still reports the same Bitcoin address and entity association.

Do not manually edit, delete or replace identity/, storage/ or ipfs/ to make this test pass.

## 6. Failure handling and rollback

Do not deliberately corrupt a live installation or its identity files. Exercise download failure, invalid archive, application test failure and rollback-failure recovery in GitHub Actions using isolated fixtures. On-device, test only a controlled cancelled download or a package whose official digest fails before execution; confirm the installer refuses to run it.

## 7. Evidence to record

Record:
- Device model and Android version (if the user chooses to disclose them).
- Termux version, architecture and Python version.
- Lobby commit SHA and official package release/tag.
- Actual /health transport result.
- Installer/updater exit status and reported application version.
- Whether the NODE ID and identity file hashes stayed constant.
- Whether local storage and Kubo/IPFS remained available.
- Widget and background lifecycle observations.

Before sharing diagnostics, inspect the report for personal identifiers. Never share private keys, tokens, private-key files, TLS private keys or raw wallet material.

## Exit criteria

The physical Termux milestone passes only when all applicable sections above are completed on a real Android ARM64 device, the identity and persistent-data checks pass across an actual update, and the observations are recorded. Ubuntu/GitHub Actions success alone is not a physical-device pass.
