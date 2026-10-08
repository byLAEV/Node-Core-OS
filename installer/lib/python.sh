#!/usr/bin/env bash
set -euo pipefail
install_application() {
  local source_dir="$1" target_dir="$NODE_CORE_DATA_DIR/app"
  rm -rf "$target_dir"
  mkdir -p "$target_dir"
  cp -R "$source_dir"/. "$target_dir"/
  rm -rf "$target_dir/.git"
}
create_launcher() {
  cat > "$NODE_CORE_DATA_DIR/bin/node-core" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export NODE_CORE_CONFIG="$NODE_CORE_DATA_DIR/config.json"
exec python3 "$NODE_CORE_DATA_DIR/app/main.py" "$@"
EOF
  chmod +x "$NODE_CORE_DATA_DIR/bin/node-core"

  cat > "$NODE_CORE_DATA_DIR/bin/node-core-update" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec bash "$NODE_CORE_DATA_DIR/app/installer/update.sh" "$@"
EOF
  chmod +x "$NODE_CORE_DATA_DIR/bin/node-core-update"
}
write_config() {
  local ipfs_executable
  if [[ -n "${NODE_CORE_KUBO_EXECUTABLE:-}" ]]; then
    ipfs_executable="$NODE_CORE_KUBO_EXECUTABLE"
  elif [[ -n "${TERMUX_VERSION:-}" && -x "${PREFIX:-}/bin/ipfs" ]]; then
    ipfs_executable="$PREFIX/bin/ipfs"
  else
    ipfs_executable="$NODE_CORE_DATA_DIR/bin/ipfs"
  fi
  cat > "$NODE_CORE_DATA_DIR/config.json" <<EOF
{
  "data_dir": "$NODE_CORE_DATA_DIR",
  "local_storage_path": "$NODE_CORE_DATA_DIR/storage",
  "ipfs_repo_path": "$NODE_CORE_DATA_DIR/ipfs",
  "ipfs_api": "$NODE_CORE_KUBO_API",
  "ipfs_gateway": "$NODE_CORE_KUBO_GATEWAY",
  "ipfs_executable": "$ipfs_executable",
  "ipfs_profile": "unixfs-v1-2025"
}
EOF
}
