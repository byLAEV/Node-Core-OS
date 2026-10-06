#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="${HOME}/.node-core"
VENV_DIR="${DATA_DIR}/venv"
APP_DIR="${DATA_DIR}/app"
BIN_DIR="${HOME}/.local/bin"
LAUNCHER="${BIN_DIR}/node-core"

. "$SCRIPT_DIR/lib/platform.sh"
. "$SCRIPT_DIR/lib/kubo.sh"

info() { printf '%s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

assert_linux_terminal || exit 1
ARCH="$(detect_linux_arch)" || fail "Unsupported Linux architecture: $(uname -m)."
command -v python3 >/dev/null 2>&1 || fail "Python 3 is required."
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required."
command -v tar >/dev/null 2>&1 || fail "tar is required."

python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10 or newer is required.")
PY

info "Node Core OS Installer"
info "byLAEV"
info
info "[1/8] Linux platform .................... OK ($ARCH)"
info "[2/8] Python 3.10+ ..................... OK"

mkdir -p "$DATA_DIR/storage" "$DATA_DIR/ipfs" "$DATA_DIR/bin" "$APP_DIR" "$BIN_DIR"

info "[3/8] Installing Node Core ............."
rm -rf "$APP_DIR/node_core" "$APP_DIR/main.py"
cp -R "$REPO_ROOT/node_core" "$APP_DIR/node_core"
cp "$REPO_ROOT/main.py" "$APP_DIR/main.py"

info "[4/8] Preparing Python runtime ........."
python3 -m venv "$VENV_DIR" || fail "Unable to create Python virtual environment."

info "[5/8] Preparing Kubo ..................."
if KUBO_EXECUTABLE="$(detect_kubo)"; then
    info "       Existing Kubo: $KUBO_EXECUTABLE"
else
    KUBO_EXECUTABLE="$(install_kubo "$ARCH")" || fail "Kubo installation failed."
    info "       Installed Kubo: $KUBO_EXECUTABLE"
fi

info "[6/8] Initializing Node Core ..........."
export NODE_CORE_CONFIG="$DATA_DIR/config.json"
PYTHONPATH="$APP_DIR" "$VENV_DIR/bin/python" - "$KUBO_EXECUTABLE" "$DATA_DIR" <<'PY'
import json, sys
from pathlib import Path
from node_core.config import NodeConfig

kubo = sys.argv[1]
data_dir = Path(sys.argv[2]).expanduser()
config = NodeConfig(
    data_dir=data_dir,
    local_storage_path=data_dir / "storage",
    ipfs_repo_path=data_dir / "ipfs",
    ipfs_executable=kubo,
)
config.save()

from node_core.ipfs import KuboManager
manager = KuboManager(
    executable=kubo,
    repo_path=config.ipfs_repo_path,
    api=config.ipfs_api,
    profile=config.ipfs_profile,
)
if not manager.is_initialized():
    manager.initialize()
print("Runtime initialized.")
PY

info "[7/8] Creating launcher ................"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$APP_DIR/main.py" "$@"
EOF
chmod 0755 "$LAUNCHER"

info "[8/8] Verifying installation ..........."
"$VENV_DIR/bin/python" -c "import node_core; from node_core.runtime import NodeRuntime; print('Node Core package: OK')"
"$KUBO_EXECUTABLE" version >/dev/null
[ -x "$LAUNCHER" ] || fail "node-core launcher was not created."

info
info "Node Core OS installed successfully."
info "Run:"
info "    node-core"
info
info "If ~/.local/bin is not in PATH, add it to your shell PATH."
