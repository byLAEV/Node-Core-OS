#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -eq 0 ]]; then
  printf '%s\n' "ERROR: Run this script as your normal Linux user, without sudo." >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
NODE_CORE_DATA_DIR="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
PYTHON="$NODE_CORE_DATA_DIR/runtime/node-core-venv/bin/python"

: "${NODE_INDEX:?Set NODE_INDEX to this machine unique index (0..N-1).}"
: "${NODE_COUNT:?Set NODE_COUNT to the total number of Linux machines.}"
: "${MESH_RUN_ID:?Set MESH_RUN_ID to the same numeric campaign ID on every machine.}"

python3 - <<'PY'
import os
import re
for name in ("NODE_INDEX", "NODE_COUNT", "MESH_RUN_ID"):
    value = os.environ[name]
    if re.fullmatch(r"[0-9]+", value) is None:
        raise SystemExit(f"ERROR: {name} must contain only digits.")
index = int(os.environ["NODE_INDEX"])
count = int(os.environ["NODE_COUNT"])
if count < 3 or count > 100 or index < 0 or index >= count:
    raise SystemExit("ERROR: NODE_COUNT must be 3..100 and NODE_INDEX must be within the roster.")
PY

if [[ ! -x "$PYTHON" ]]; then
  printf 'ERROR: Node Core OS virtual environment not found: %s\n' "$PYTHON" >&2
  printf '%s\n' "Install Node Core OS first with: bash installer/install.sh" >&2
  exit 1
fi

if ! command -v tailscale >/dev/null 2>&1; then
  printf '%s\n' "ERROR: Tailscale CLI is not installed on this Linux machine." >&2
  exit 1
fi

TAILSCALE_IP="$(tailscale ip -4 | head -n 1)"
if [[ -z "$TAILSCALE_IP" ]]; then
  printf '%s\n' "ERROR: This machine is not connected to the Tailscale network." >&2
  exit 1
fi

export NODE_CORE_DATA_DIR
export PYTHONPATH="$NODE_CORE_DATA_DIR/app"
export RUNNER_TEMP="${RUNNER_TEMP:-$NODE_CORE_DATA_DIR/logs}"

ARGS=(
  "$REPOSITORY_ROOT/ci/linux/real_multi_node_mesh.py"
  --index "$NODE_INDEX"
  --count "$NODE_COUNT"
  --run-id "$MESH_RUN_ID"
)

if [[ "$NODE_INDEX" != "0" ]]; then
  : "${MESH_COORDINATOR_IP:?Set MESH_COORDINATOR_IP to Tailscale IPv4 address of node 0.}"
  ARGS+=(--coordinator-ip "$MESH_COORDINATOR_IP")
fi

printf '%s\n' "Node Core OS manual Linux mesh participant"
printf 'node_index=%s\nnode_count=%s\nrun_id=%s\ntailscale_ipv4=%s\nuid=%s\nhostname=%s\n' \
  "$NODE_INDEX" "$NODE_COUNT" "$MESH_RUN_ID" "$TAILSCALE_IP" "$(id -u)" "$(hostname)"

"$PYTHON" -m py_compile "$REPOSITORY_ROOT/ci/linux/real_multi_node_mesh.py"
exec "$PYTHON" "${ARGS[@]}"
