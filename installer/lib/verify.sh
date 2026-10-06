#!/usr/bin/env bash
set -euo pipefail
verify_installation() {
  local failures=0
  [[ "$(uname -s)" == "Linux" ]] || failures=1
  python3 -m compileall -q "$NODE_CORE_DATA_DIR/app/main.py" "$NODE_CORE_DATA_DIR/app/node_core" || failures=1
  [[ -x "$NODE_CORE_DATA_DIR/bin/node-core" ]] || failures=1
  [[ -x "$NODE_CORE_DATA_DIR/bin/ipfs" ]] || failures=1
  export IPFS_PATH="$NODE_CORE_DATA_DIR/ipfs"
  [[ -f "$IPFS_PATH/config" ]] || failures=1
  return "$failures"
}
