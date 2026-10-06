#!/usr/bin/env bash
set -euo pipefail

NODE_CORE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="${HOME}/.local/bin"
DATA_DIR="${HOME}/.node-core"

info() { printf '%s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || fail "Python 3 is required."
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10 or newer is required.")
PY

mkdir -p "$INSTALL_DIR" "$DATA_DIR"
python3 -m pip --version >/dev/null 2>&1 || fail "python3 -m pip is required."

info "Node Core OS Installer"
info "byLAEV"
info
info "[1/5] Installing Node Core package..."
python3 -m pip install --user --upgrade "$NODE_CORE_ROOT"

info "[2/5] Preparing Node Core data directory..."
mkdir -p "$DATA_DIR/storage" "$DATA_DIR/ipfs"

info "[3/5] Checking launcher..."
if [ ! -x "$INSTALL_DIR/node-core" ]; then
    # pip may place the launcher elsewhere; locate the installed script.
    SCRIPT_PATH="$(python3 - <<'PY'
import os, sysconfig
for base in filter(None, [sysconfig.get_path("scripts"), os.path.expanduser("~/.local/bin")]):
    candidate=os.path.join(base, "node-core")
    if os.path.isfile(candidate):
        print(candidate)
        break
else:
    raise SystemExit(1)
PY
)"
    if [ "$SCRIPT_PATH" != "$INSTALL_DIR/node-core" ]; then
        cp "$SCRIPT_PATH" "$INSTALL_DIR/node-core"
        chmod +x "$INSTALL_DIR/node-core"
    fi
fi

info "[4/5] Initializing Node Core..."
PYTHONPATH="$NODE_CORE_ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 - <<'PY'
from node_core.runtime import NodeRuntime
NodeRuntime().boot()
print("Runtime initialized.")
PY

info "[5/5] Verifying installation..."
test -x "$INSTALL_DIR/node-core" || fail "node-core launcher was not installed."
python3 -m pip show node-core-os >/dev/null 2>&1 || fail "Node Core package verification failed."

info
info "Node Core OS installed successfully."
info
info "Run:"
info "    node-core"
info
info "If ~/.local/bin is not in PATH, add it to your shell PATH."
