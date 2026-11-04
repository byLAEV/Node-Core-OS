#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS installer helpers cannot run as root. Use the normal user account without sudo.\n' >&2
  return 1 2>/dev/null || exit 1
fi

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
  local failures=0 executable app_dir python_environment
  app_dir="$NODE_CORE_DATA_DIR/app"
  python_environment="$NODE_CORE_DATA_DIR/runtime/node-core-venv/bin/python"
  executable="${NODE_CORE_KUBO_EXECUTABLE:-$NODE_CORE_DATA_DIR/bin/ipfs}"

  check_file() {
    if [[ ! -f "$1" ]]; then
      printf 'Verification failed: required file is missing: %s\n' "$1" >&2
      failures=1
    fi
  }
  check_executable() {
    if [[ ! -x "$1" ]]; then
      printf 'Verification failed: required executable is missing or not executable: %s\n' "$1" >&2
      failures=1
    fi
  }

  if [[ "$(uname -s)" != "Linux" ]]; then
    printf 'Verification failed: expected Linux, found %s.\n' "$(uname -s)" >&2
    failures=1
  fi

  check_file "$app_dir/node_core/evidence.py"
  check_file "$app_dir/node_core/my_life.py"
  check_file "$app_dir/node_core/identity/profile.py"
  check_file "$app_dir/VERSION"

  if [[ -f "$app_dir/VERSION" ]]; then
    local app_version
    app_version="$(cat "$app_dir/VERSION")"
    if [[ ! "$app_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      printf 'Verification failed: invalid application VERSION: %s\n' "$app_version" >&2
      failures=1
    fi
  fi

  if [[ ! -x "$python_environment" ]]; then
    printf 'Verification failed: Node Core private Python interpreter is missing: %s\n' "$python_environment" >&2
    failures=1
  else
    if ! "$python_environment" -c 'import cryptography; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; Ed25519PrivateKey.generate()'; then
      printf 'Verification failed: cryptography/Ed25519 is unavailable in the application runtime.\n' >&2
      failures=1
    fi
    if ! "$python_environment" -m compileall -q "$app_dir/main.py" "$app_dir/node_core"; then
      printf 'Verification failed: Python compilation failed for the installed application.\n' >&2
      failures=1
    fi
  fi

  check_executable "$NODE_CORE_DATA_DIR/bin/node-core"
  check_executable "$executable"

  export IPFS_PATH="$NODE_CORE_DATA_DIR/ipfs"
  check_file "$IPFS_PATH/config"

  if ! wait_for_kubo_api; then
    printf 'Verification failed: Kubo API is not reachable after startup retries at %s.\n' "$NODE_CORE_KUBO_API" >&2
    if [[ -f "$NODE_CORE_DATA_DIR/logs/kubo.log" ]]; then
      printf '%s\n' '--- Kubo startup log ---' >&2
      cat "$NODE_CORE_DATA_DIR/logs/kubo.log" >&2
    fi
    failures=1
  fi

  if [[ "$failures" -eq 0 ]]; then
    printf 'Installation verification passed.\n'
  fi
  return "$failures"
}
