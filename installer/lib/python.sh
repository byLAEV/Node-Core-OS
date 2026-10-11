#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS installer helpers cannot run as root. Use the normal user account without sudo.\\n' >&2
  return 1 2>/dev/null || exit 1
fi

install_application() {
  local source_dir="$1" target_dir="$NODE_CORE_DATA_DIR/app"
  if [[ -L "$target_dir" || ( -e "$target_dir" && ! -d "$target_dir" ) ]]; then
    printf 'Unsafe application path: %s is not a real directory.\n' "$target_dir" >&2
    return 1
  fi
  if [[ -d "$target_dir" ]] && [[ -n "$(find "$target_dir" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    printf 'An application already exists at %s. Use node-core-update to update it safely.\n' "$target_dir" >&2
    return 1
  fi
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

  cat > "$NODE_CORE_DATA_DIR/bin/hashpaper" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export NODE_CORE_DATA_DIR="$NODE_CORE_DATA_DIR"
export PATH="$NODE_CORE_DATA_DIR/runtime/opentimestamps-venv/bin:$PATH"
exec python3 "$NODE_CORE_DATA_DIR/app/applications/hashpaper/main.py" "\$@"
EOF
  chmod 700 "$NODE_CORE_DATA_DIR/bin/hashpaper"
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
