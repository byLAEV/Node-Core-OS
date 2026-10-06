#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/lib/kubo.sh"

NODE_CORE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${HOME}/.node-core"
VENV_DIR="${DATA_DIR}/venv"
BIN_DIR="${HOME}/.local/bin"
LAUNCHER="${BIN_DIR}/node-core"

info() { printf '%s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[ "$(uname -s)" = "Linux" ] || fail "Node Core OS Installer v1 supports GNU/Linux terminals only."
command -v python3 >/dev/null 2>&1 || fail "Python 3 is required."

python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10 or newer is required.")
PY

info "Node Core OS Installer"
info "byLAEV"
info

info "[1/6] Detecting Linux environment ........ OK"
info "[2/6] Checking Python ................... OK"

mkdir -p "$DATA_DIR/storage" "$DATA_DIR/ipfs" "$BIN_DIR"

info "[3/6] Creating Node Core environment ...."
python3 -m venv "$VENV_DIR" || fail "Unable to create the Node Core Python environment."
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/python" -m pip install --upgrade "$NODE_CORE_ROOT"

info "[4/6] Preparing launcher ................"
if KUBO_EXECUTABLE="$(detect_kubo)"; then
    info "       Kubo detected: $KUBO_EXECUTABLE"
    KUBO_VERSION="$(kubo_version "$KUBO_EXECUTABLE" || true)"
    [ -n "$KUBO_VERSION" ] && info "       Kubo version: $KUBO_VERSION"
else
    info "       Kubo not detected; Node Core will remain in Kubo-unavailable state."
fi
ln -sfn "$VENV_DIR/bin/node-core" "$LAUNCHER"
chmod +x "$LAUNCHER"

info "[5/6] Initializing Node Runtime ........"
"$VENV_DIR/bin/python" - <<'PY'
from node_core.runtime import NodeRuntime
NodeRuntime().boot()
print("Runtime initialized.")
PY

info "[6/6] Verifying installation ..........."
[ -x "$LAUNCHER" ] || fail "node-core launcher was not created."
"$VENV_DIR/bin/python" -c "import node_core; print('Node Core package: OK')"

info
info "Node Core OS installed successfully."
info
info "Run:"
info "    node-core"
info
info "If ~/.local/bin is not in PATH, add it to your shell PATH."
