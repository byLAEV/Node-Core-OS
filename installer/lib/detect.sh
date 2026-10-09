#!/usr/bin/env bash
set -euo pipefail

# This module is intentionally read-only. It describes the current installation
# and never creates directories, repairs files, downloads code, or starts Kubo.

node_core_detect_installation() {
  local data_dir="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
  local app_dir="$data_dir/app"
  local executable=""
  local config_file="$data_dir/config.json"

  NODE_CORE_DETECT_APP="missing"
  NODE_CORE_DETECT_LAUNCHER="missing"
  NODE_CORE_DETECT_UPDATE_LAUNCHER="missing"
  NODE_CORE_DETECT_KUBO="missing"
  NODE_CORE_DETECT_IPFS_REPOSITORY="missing"
  NODE_CORE_DETECT_LOCAL_STORAGE="missing"
  NODE_CORE_DETECT_CONFIG="missing"
  NODE_CORE_DETECT_MANIFEST="missing"
  NODE_CORE_DETECT_COMMIT="unknown"

  if [[ -f "$app_dir/main.py" && -d "$app_dir/node_core" ]]; then
    NODE_CORE_DETECT_APP="present"
  elif [[ -d "$app_dir" ]]; then
    NODE_CORE_DETECT_APP="incomplete"
  fi

  [[ -x "$data_dir/bin/node-core" ]] && NODE_CORE_DETECT_LAUNCHER="present"
  [[ -x "$data_dir/bin/node-core-update" ]] && NODE_CORE_DETECT_UPDATE_LAUNCHER="present"

  if [[ -n "${TERMUX_VERSION:-}" && -n "${PREFIX:-}" && -x "$PREFIX/bin/ipfs" ]]; then
    executable="$PREFIX/bin/ipfs"
  elif [[ -x "$data_dir/bin/ipfs" ]]; then
    executable="$data_dir/bin/ipfs"
  fi
  if [[ -n "$executable" ]]; then
    NODE_CORE_DETECT_KUBO="present"
    NODE_CORE_DETECT_KUBO_PATH="$executable"
  else
    NODE_CORE_DETECT_KUBO_PATH=""
  fi

  [[ -f "$data_dir/ipfs/config" ]] && NODE_CORE_DETECT_IPFS_REPOSITORY="present"
  [[ -d "$data_dir/storage" ]] && NODE_CORE_DETECT_LOCAL_STORAGE="present"

  if [[ -f "$config_file" ]]; then
    if python3 - "$config_file" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    value = json.load(stream)
if not isinstance(value, dict):
    raise SystemExit(1)
PY
    then
      NODE_CORE_DETECT_CONFIG="valid"
    else
      NODE_CORE_DETECT_CONFIG="invalid"
    fi
  fi

  [[ -f "$data_dir/installation-manifest.json" ]] && NODE_CORE_DETECT_MANIFEST="present"
  if [[ -f "$data_dir/runtime/node-core-commit" ]]; then
    NODE_CORE_DETECT_COMMIT="$(cat "$data_dir/runtime/node-core-commit")"
    [[ -n "$NODE_CORE_DETECT_COMMIT" ]] || NODE_CORE_DETECT_COMMIT="unknown"
  fi

  printf 'application=%s\n' "$NODE_CORE_DETECT_APP"
  printf 'launcher=%s\n' "$NODE_CORE_DETECT_LAUNCHER"
  printf 'update_launcher=%s\n' "$NODE_CORE_DETECT_UPDATE_LAUNCHER"
  printf 'kubo=%s\n' "$NODE_CORE_DETECT_KUBO"
  printf 'kubo_path=%s\n' "$NODE_CORE_DETECT_KUBO_PATH"
  printf 'ipfs_repository=%s\n' "$NODE_CORE_DETECT_IPFS_REPOSITORY"
  printf 'local_storage=%s\n' "$NODE_CORE_DETECT_LOCAL_STORAGE"
  printf 'configuration=%s\n' "$NODE_CORE_DETECT_CONFIG"
  printf 'manifest=%s\n' "$NODE_CORE_DETECT_MANIFEST"
  printf 'installed_commit=%s\n' "$NODE_CORE_DETECT_COMMIT"
}
