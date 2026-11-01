#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'FAIL: offline updater E2E must run as a normal user.\n' >&2
  exit 1
fi

UPDATE_PACKAGE="${1:-}"
[[ -n "$UPDATE_PACKAGE" && -f "$UPDATE_PACKAGE" ]] || {
  printf 'Usage: bash installer/tests/offline-updater-e2e.sh <update-package.tar.gz>\n' >&2
  exit 2
}

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEMP_ROOT"' EXIT

export HOME="$TEMP_ROOT/home"
export NODE_CORE_DATA_DIR="$HOME/.node-core"
mkdir -p "$HOME" "$NODE_CORE_DATA_DIR/app/node_core" "$NODE_CORE_DATA_DIR/storage" \
  "$NODE_CORE_DATA_DIR/ipfs" "$NODE_CORE_DATA_DIR/bin" "$NODE_CORE_DATA_DIR/runtime" \
  "$TEMP_ROOT/package" "$TEMP_ROOT/fake-bin"

# Seed a minimal existing installation and user data that must survive the update.
printf 'print("old Node Core application")\n' > "$NODE_CORE_DATA_DIR/app/main.py"
printf '1.0.0\n' > "$NODE_CORE_DATA_DIR/app/VERSION"
printf 'old requirement fixture\n' > "$NODE_CORE_DATA_DIR/app/requirements.txt"
printf 'preserve local storage\n' > "$NODE_CORE_DATA_DIR/storage/user-data.txt"
printf 'preserve Kubo repository\n' > "$NODE_CORE_DATA_DIR/ipfs/config"
printf '{"custom":"preserve"}\n' > "$NODE_CORE_DATA_DIR/config.json"
cat > "$NODE_CORE_DATA_DIR/bin/ipfs" <<'IPFS'
#!/usr/bin/env bash
printf 'Kubo fixture\n'
IPFS
chmod +x "$NODE_CORE_DATA_DIR/bin/ipfs"

# Extract the exact release updater package; it must contain its source archive and commit marker.
tar -xzf "$UPDATE_PACKAGE" -C "$TEMP_ROOT/package"
UPDATE_DIR="$(find "$TEMP_ROOT/package" -mindepth 1 -maxdepth 1 -type d -print -quit)"
[[ -n "$UPDATE_DIR" && -f "$UPDATE_DIR/update.sh" && -f "$UPDATE_DIR/source-package.tar.gz" && -f "$UPDATE_DIR/SOURCE_COMMIT" ]] || {
  printf 'FAIL: update package is missing update.sh, source-package.tar.gz, or SOURCE_COMMIT.\n' >&2
  exit 1
}
IFS= read -r EXPECTED_COMMIT < "$UPDATE_DIR/SOURCE_COMMIT"
[[ "$EXPECTED_COMMIT" =~ ^[0-9a-fA-F]{40}$ ]] || {
  printf 'FAIL: invalid SOURCE_COMMIT in update package.\n' >&2
  exit 1
}
tar -tzf "$UPDATE_DIR/source-package.tar.gz" >/dev/null

# Replace every normal network transport command with a hard failure.
for command_name in curl wget git; do
  cat > "$TEMP_ROOT/fake-bin/$command_name" <<'NO_NETWORK'
#!/usr/bin/env bash
printf 'FAIL: network command attempted during offline updater test: %s\n' "$0" >&2
exit 97
NO_NETWORK
  chmod +x "$TEMP_ROOT/fake-bin/$command_name"
done
export PATH="$TEMP_ROOT/fake-bin:$PATH"

# The actual release updater must consume its adjacent bundled source snapshot.
printf 'y\n' | bash "$UPDATE_DIR/update.sh" > "$TEMP_ROOT/updater.log" 2>&1 || {
  cat "$TEMP_ROOT/updater.log" >&2
  exit 1
}
cat "$TEMP_ROOT/updater.log"

# Verify source activation, dependency import, and commit pinning.
[[ -f "$NODE_CORE_DATA_DIR/app/main.py" ]]
[[ -f "$NODE_CORE_DATA_DIR/app/installer/update.sh" ]]
[[ -f "$NODE_CORE_DATA_DIR/app/requirements.txt" ]]
grep -qx "$EXPECTED_COMMIT" "$NODE_CORE_DATA_DIR/runtime/node-core-commit"
"$NODE_CORE_DATA_DIR/runtime/node-core-venv/bin/python" -c 'import cryptography; print("Verified offline cryptography dependency:", cryptography.__version__)'

# Verify persistent data and Kubo are not replaced by the application update.
grep -qx 'preserve local storage' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
grep -qx 'preserve Kubo repository' "$NODE_CORE_DATA_DIR/ipfs/config"
grep -qx '{"custom":"preserve"}' "$NODE_CORE_DATA_DIR/config.json"
grep -q 'Kubo fixture' "$NODE_CORE_DATA_DIR/bin/ipfs"

# Recovery state must be clean after a successful update.
test ! -e "$NODE_CORE_DATA_DIR/runtime/update/app-backup"
test ! -e "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-backup"
test ! -e "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-state"

printf 'PASS: bundled updater completed with network transports blocked.\n'
printf 'PASS: SOURCE_COMMIT matched the installed commit marker.\n'
printf 'PASS: offline Python dependencies were installed from the bundled wheelhouse.\n'
printf 'PASS: local storage, Kubo repository, executable, and configuration were preserved.\n'
