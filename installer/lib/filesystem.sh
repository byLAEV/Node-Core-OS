#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS installer helpers cannot run as root. Use the normal user account without sudo.\\n' >&2
  return 1 2>/dev/null || exit 1
fi

prepare_filesystem() {
  mkdir -p "$NODE_CORE_DATA_DIR/app" "$NODE_CORE_DATA_DIR/bin" "$NODE_CORE_DATA_DIR/storage" "$NODE_CORE_DATA_DIR/ipfs" "$NODE_CORE_DATA_DIR/logs" "$NODE_CORE_DATA_DIR/runtime" "$NODE_CORE_DATA_DIR/services"
}
