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
exec python3 "$NODE_CORE_DATA_DIR/app/main.py" "$@"
EOF
  chmod +x "$NODE_CORE_DATA_DIR/bin/node-core"
}
write_config() {
  cat > "$NODE_CORE_DATA_DIR/config.json" <<EOF
{
  "data_dir": "$NODE_CORE_DATA_DIR",
  "local_storage_path": "$NODE_CORE_DATA_DIR/storage",
  "ipfs_repo_path": "$NODE_CORE_DATA_DIR/ipfs",
  "ipfs_api": "$NODE_CORE_KUBO_API",
  "ipfs_gateway": "$NODE_CORE_KUBO_GATEWAY",
  "ipfs_executable": "$NODE_CORE_DATA_DIR/bin/ipfs",
  "ipfs_profile": "unixfs-v1-2025"
}
EOF
}
