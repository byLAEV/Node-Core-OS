#!/usr/bin/env bash
set -euo pipefail
prepare_filesystem() {
  mkdir -p "$NODE_CORE_DATA_DIR/app" "$NODE_CORE_DATA_DIR/bin" "$NODE_CORE_DATA_DIR/storage" "$NODE_CORE_DATA_DIR/ipfs" "$NODE_CORE_DATA_DIR/logs" "$NODE_CORE_DATA_DIR/runtime" "$NODE_CORE_DATA_DIR/services"
}
