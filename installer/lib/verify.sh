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

verify_check() {
  local label="$1"
  shift
  if "$@"; then
    printf '[OK] %s\n' "$label"
    return 0
  fi
  printf '[FAIL] %s\n' "$label" >&2
  return 1
}

verify_python_application() {
  python3 -m compileall -q \
    "$NODE_CORE_DATA_DIR/app/main.py" \
    "$NODE_CORE_DATA_DIR/app/node_core"
}

verify_age() {
  [[ -x "$NODE_CORE_DATA_DIR/bin/age" ]] &&
    [[ "$("$NODE_CORE_DATA_DIR/bin/age" --version)" == "v\${NODE_CORE_AGE_VERSION}" ]]
}

verify_kubo_api() {
  if wait_for_kubo_api; then
    return 0
  fi
  if [[ -f "$NODE_CORE_DATA_DIR/logs/kubo.log" ]]; then
    printf '%s\n' '--- Kubo startup log ---' >&2
    cat "$NODE_CORE_DATA_DIR/logs/kubo.log" >&2
  fi
  return 1
}

verify_installation() {
  local failures=0
  export IPFS_PATH="$NODE_CORE_DATA_DIR/ipfs"

  printf '%s\n' 'Node Core OS installation verification'

  verify_check 'Linux platform' test "$(uname -s)" = Linux || failures=1
  verify_check 'Python application' verify_python_application || failures=1
  verify_check 'Node Core launcher' test -x "$NODE_CORE_DATA_DIR/bin/node-core" || failures=1
  verify_check 'Kubo binary' test -x "$NODE_CORE_DATA_DIR/bin/ipfs" || failures=1
  verify_check 'age binary and version' verify_age || failures=1
  verify_check 'IPFS repository' test -f "$IPFS_PATH/config" || failures=1
  verify_check 'Backups directory' test -d "$NODE_CORE_DATA_DIR/backups" || failures=1
  verify_check 'Secrets directory' test -d "$NODE_CORE_DATA_DIR/secrets" || failures=1
  verify_check 'Backups permissions' test "$(stat -c '%a' "$NODE_CORE_DATA_DIR/backups" 2>/dev/null || true)" = 700 || failures=1
  verify_check 'Secrets permissions' test "$(stat -c '%a' "$NODE_CORE_DATA_DIR/secrets" 2>/dev/null || true)" = 700 || failures=1
  verify_check 'Kubo API' verify_kubo_api || failures=1

  if (( failures == 0 )); then
    printf '%s\n' 'Installation verification passed.'
    return 0
  fi

  printf '%s\n' 'Installation verification failed.' >&2
  return 1
}
