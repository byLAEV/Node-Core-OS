#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/workspace}"
export HOME="${HOME:-/home/nodecore}"
export NODE_CORE_DATA_DIR="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
export NODE_CORE_CONFIG="$NODE_CORE_DATA_DIR/config.json"
export IPFS_PATH="$NODE_CORE_DATA_DIR/ipfs"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ERROR: Node Core OS tests must run as an ordinary Linux user (UID != 0)." >&2
  exit 1
fi

cd "$PROJECT_ROOT"
. /etc/os-release
printf 'Distribution: %s %s (%s)\n' "$NAME" "$VERSION_ID" "$ID"
printf 'Execution user: %s (uid=%s, gid=%s)\n' "$(id -un)" "$(id -u)" "$(id -g)"
printf 'Kernel: %s\n' "$(uname -sr)"
test "$(id -un)" = nodecore
test "$ID" = "${EXPECTED_OS_ID}"
case "$ID:$VERSION_ID" in
  ubuntu:24.04|debian:13|fedora:44) ;;
  *) echo "Unexpected distribution/version: $ID $VERSION_ID" >&2; exit 1 ;;
esac

for command_name in bash python3 tar sha512sum mkdir cp rm mktemp uname awk realpath stat id curl; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "Missing test prerequisite: $command_name" >&2
    exit 1
  }
done

echo "=== Installer shell syntax ==="
bash installer/tests/syntax.sh
bash installer/tests/user-context.sh

echo "=== Source compilation and complete unit suite (ordinary user) ==="
python3 -m compileall -q main.py node_core tests
python3 -m unittest discover -s tests -v

echo "=== Clean real installation (ordinary user) ==="
mkdir -p "$HOME"
bash installer/install.sh

test -x "$NODE_CORE_DATA_DIR/bin/node-core"
test -x "$NODE_CORE_DATA_DIR/bin/node-core-update"
test -x "$NODE_CORE_DATA_DIR/bin/ipfs"
test -f "$NODE_CORE_DATA_DIR/config.json"
test -f "$NODE_CORE_DATA_DIR/ipfs/config"
test -d "$NODE_CORE_DATA_DIR/storage"
test "$(stat -c '%u' "$NODE_CORE_DATA_DIR")" = "$(id -u)"
test -z "$(find "$NODE_CORE_DATA_DIR" -xdev -uid 0 -print -quit)"
"$NODE_CORE_DATA_DIR/bin/ipfs" version
"$NODE_CORE_DATA_DIR/bin/ipfs" id >/dev/null
curl --fail --silent --show-error --max-time 10 -X POST \
  http://127.0.0.1:5001/api/v0/id >/dev/null

echo "=== Installed BIOS menu smoke test ==="
menu_log="$RUNNER_TEMP/node-core-bios-menu.txt"
printf '1\n0\n0\n' | "$NODE_CORE_DATA_DIR/bin/node-core" > "$menu_log"
grep -Fq 'Node Core BIOS' "$menu_log"
grep -Fq 'GitHub Identity Pool' "$menu_log"

echo "=== Installed application test suite ==="
cd "$NODE_CORE_DATA_DIR/app"
"$NODE_CORE_DATA_DIR/runtime/node-core-venv/bin/python" -m unittest discover -s tests -v

echo "=== Verify persistent node identity before/after update ==="
identity_before="$("$NODE_CORE_DATA_DIR/runtime/node-core-venv/bin/python" - <<'PY'
import os
from pathlib import Path
from node_core.identity.node_identity import NodeIdentityStore
print(NodeIdentityStore(Path(os.environ["NODE_CORE_DATA_DIR"])).load()["node_id"])
PY
)"
printf 'test persistence marker\n' > "$NODE_CORE_DATA_DIR/storage/linux-matrix-preservation.txt"
storage_before="$(sha256sum "$NODE_CORE_DATA_DIR/storage/linux-matrix-preservation.txt" | awk '{print $1}')"
echo "Node ID before update: $identity_before"

echo "=== Real update from the exact PR branch (ordinary user) ==="
cd "$PROJECT_ROOT"
printf 'y\n' | NODE_CORE_BRANCH="$NODE_CORE_BRANCH" bash "$NODE_CORE_DATA_DIR/app/installer/update.sh"

identity_after="$("$NODE_CORE_DATA_DIR/runtime/node-core-venv/bin/python" - <<'PY'
import os
from pathlib import Path
from node_core.identity.node_identity import NodeIdentityStore
print(NodeIdentityStore(Path(os.environ["NODE_CORE_DATA_DIR"])).load()["node_id"])
PY
)"
storage_after="$(sha256sum "$NODE_CORE_DATA_DIR/storage/linux-matrix-preservation.txt" | awk '{print $1}')"
test "$identity_before" = "$identity_after"
test "$storage_before" = "$storage_after"
test "$(stat -c '%u' "$NODE_CORE_DATA_DIR")" = "$(id -u)"
test -z "$(find "$NODE_CORE_DATA_DIR" -xdev -uid 0 -print -quit)"

echo "=== Final installed suite after update ==="
cd "$NODE_CORE_DATA_DIR/app"
"$NODE_CORE_DATA_DIR/runtime/node-core-venv/bin/python" -m unittest discover -s tests -v

echo "=== Clean uninstall (ordinary user) ==="
cd "$PROJECT_ROOT"
printf 'REMOVE\n' | bash installer/uninstall.sh
test ! -e "$NODE_CORE_DATA_DIR"
printf 'PASS: %s install, BIOS, Kubo, identity persistence, update, tests and uninstall as uid=%s\n' "$ID $VERSION_ID" "$(id -u)"
