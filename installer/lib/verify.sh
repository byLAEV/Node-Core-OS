#!/usr/bin/env bash
set -euo pipefail

wait_for_kubo_api() {
  local attempt
  for attempt in {1..20}; do
    if http_post "$NODE_CORE_KUBO_API/api/v0/id" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

verify_installation() {
  local failures=0
  [[ "$(uname -s)" == "Linux" ]] || failures=1
  python3 -m compileall -q "$NODE_CORE_DATA_DIR/app/main.py" "$NODE_CORE_DATA_DIR/app/node_core" || failures=1
  [[ -x "$NODE_CORE_DATA_DIR/bin/node-core" ]] || failures=1
  [[ -x "$NODE_CORE_DATA_DIR/bin/ipfs" ]] || failures=1
  export IPFS_PATH="$NODE_CORE_DATA_DIR/ipfs"
  [[ -f "$IPFS_PATH/config" ]] || failures=1
  if ! wait_for_kubo_api; then
    printf 'Verification failed: Kubo API is not reachable after startup retries.\n' >&2
    if [[ -f "$NODE_CORE_DATA_DIR/logs/kubo.log" ]]; then
      printf '%s\n' '--- Kubo startup log ---' >&2
      cat "$NODE_CORE_DATA_DIR/logs/kubo.log" >&2
    fi
    failures=1
  fi
  return "$failures"
}
