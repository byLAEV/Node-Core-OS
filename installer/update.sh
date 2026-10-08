#!/usr/bin/env bash
set -euo pipefail

NODE_CORE_REPOSITORY="${NODE_CORE_REPOSITORY:-https://github.com/byLAEV/Node-Core-OS}"
NODE_CORE_BRANCH="${NODE_CORE_BRANCH:-main}"
NODE_CORE_DATA_DIR="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
NODE_CORE_APP_DIR="$NODE_CORE_DATA_DIR/app"
NODE_CORE_UPDATE_DIR="$NODE_CORE_DATA_DIR/runtime/update"
NODE_CORE_COMMIT_FILE="$NODE_CORE_DATA_DIR/runtime/node-core-commit"

download_file() {
  local url="$1" destination="$2"
  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --silent --show-error \
      --connect-timeout 15 --retry 3 --retry-delay 2 --retry-all-errors \
      --output "$destination" "$url"
  else
    wget --quiet --connect-timeout=15 --tries=4 --waitretry=2 \
      --output-document="$destination" "$url"
  fi
}

resolve_kubo_executable() {
  if [[ -n "${TERMUX_VERSION:-}" && -n "${PREFIX:-}" && -x "$PREFIX/bin/ipfs" ]]; then
    printf '%s\n' "$PREFIX/bin/ipfs"
    return 0
  fi
  printf '%s\n' "$NODE_CORE_DATA_DIR/bin/ipfs"
}

require_installation() {
  [[ -d "$NODE_CORE_APP_DIR" ]] || {
    printf 'Node Core OS installation not found: %s\n' "$NODE_CORE_DATA_DIR" >&2
    exit 1
  }
  local executable
  executable="$(resolve_kubo_executable)"
  [[ -x "$executable" ]] || {
    printf 'Kubo/IPFS executable not found: %s\n' "$executable" >&2
    printf 'Aborting update to protect the installation.\n' >&2
    exit 1
  }
  [[ -d "$NODE_CORE_DATA_DIR/ipfs" ]] || {
    printf 'Kubo repository not found. Aborting update to protect the installation.\n' >&2
    exit 1
  }
  [[ -d "$NODE_CORE_DATA_DIR/storage" ]] || {
    printf 'Local storage not found. Aborting update to protect the installation.\n' >&2
    exit 1
  }
}

ensure_launchers() {
  mkdir -p "$NODE_CORE_DATA_DIR/bin"

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

migrate_termux_config() {
  local config="$NODE_CORE_DATA_DIR/config.json"
  local executable
  executable="$(resolve_kubo_executable)"
  [[ -n "${TERMUX_VERSION:-}" && -x "$executable" && -f "$config" ]] || return 0

  if ! "$executable" version >/dev/null 2>&1; then
    printf 'Termux Kubo executable failed verification: %s\n' "$executable" >&2
    return 1
  fi

  python3 - "$config" "$executable" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
executable = sys.argv[2]
data = json.loads(path.read_text(encoding="utf-8"))
if data.get("ipfs_executable") != executable:
    data["ipfs_executable"] = executable
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

latest_commit() {
  local response="$NODE_CORE_UPDATE_DIR/latest-commit.json"
  mkdir -p "$NODE_CORE_UPDATE_DIR"
  download_file \
    "https://api.github.com/repos/byLAEV/Node-Core-OS/commits/$NODE_CORE_BRANCH" \
    "$response"
  python3 - "$response" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
print(data["sha"])
PY
}

backup_app() {
  local backup="$NODE_CORE_UPDATE_DIR/app-backup"
  rm -rf "$backup"
  cp -R "$NODE_CORE_APP_DIR" "$backup"
  printf '%s\n' "$backup"
}

update_application() {
  local commit="$1"
  local archive="$NODE_CORE_UPDATE_DIR/source.tar.gz"
  local extract="$NODE_CORE_UPDATE_DIR/source"

  rm -rf "$extract"
  mkdir -p "$extract"
  download_file \
    "https://github.com/byLAEV/Node-Core-OS/archive/$commit.tar.gz" \
    "$archive"
  tar -xzf "$archive" -C "$extract"

  local source
  source="$(find "$extract" -mindepth 1 -maxdepth 1 -type d -print -quit)"
  [[ -n "$source" ]] || {
    printf 'Update archive did not contain the Node Core OS source.\n' >&2
    return 1
  }

  rm -rf "$NODE_CORE_APP_DIR"
  mkdir -p "$NODE_CORE_APP_DIR"
  cp -R "$source"/. "$NODE_CORE_APP_DIR"/
  rm -rf "$NODE_CORE_APP_DIR/.git"

  python3 -m compileall -q "$NODE_CORE_APP_DIR/main.py" "$NODE_CORE_APP_DIR/node_core"
  printf '%s\n' "$commit" > "$NODE_CORE_COMMIT_FILE"
}

rollback_application() {
  local backup="$NODE_CORE_UPDATE_DIR/app-backup"
  [[ -d "$backup" ]] || return 1
  rm -rf "$NODE_CORE_APP_DIR"
  cp -R "$backup" "$NODE_CORE_APP_DIR"
}

cleanup_update_files() {
  rm -rf "$NODE_CORE_UPDATE_DIR/source" "$NODE_CORE_UPDATE_DIR/app-backup"
  rm -f "$NODE_CORE_UPDATE_DIR/source.tar.gz" "$NODE_CORE_UPDATE_DIR/latest-commit.json"
}

main() {
  printf '%s\n' 'Node Core OS updater'
  printf '%s\n' 'byLAEV'
  printf '\n'
  require_installation
  migrate_termux_config
  ensure_launchers

  local remote_commit local_commit
  remote_commit="$(latest_commit)"
  local_commit=''

  if [[ -f "$NODE_CORE_COMMIT_FILE" ]]; then
    local_commit="$(cat "$NODE_CORE_COMMIT_FILE")"
  fi

  printf 'Installed Node Core commit: %s\n' "${local_commit:-unknown}"
  printf 'Available Node Core commit: %s\n' "$remote_commit"
  printf '\n'

  if [[ -n "$local_commit" && "$local_commit" == "$remote_commit" ]]; then
    printf 'Node Core OS is already up to date.\n'
    cleanup_update_files
    return 0
  fi

  printf '%s\n' 'An application update is available.'
  printf '%s\n' 'The updater will modify only the Node Core application.'
  printf '%s\n' 'Kubo/IPFS binary, IPFS repository, and local storage will not be replaced.'
  printf '%s\n' 'On Termux, config.json may be migrated only to point Node Core to the existing Android-compatible Kubo executable.'
  printf '\n'
  read -r -p 'Update Node Core OS? [Y/n] ' answer
  case "${answer:-y}" in
    y|Y|yes|YES) ;;
    *) printf 'Update cancelled.\n'; cleanup_update_files; return 0 ;;
  esac

  local backup
  backup="$(backup_app)"

  if update_application "$remote_commit"; then
    printf '\n✓ Node Core application updated.\n'
    printf '✓ Kubo/IPFS binary preserved.\n'
    printf '✓ Kubo repository preserved.\n'
    printf '✓ Local storage preserved.\n'
    printf '✓ Configuration preserved unless Termux executable path migration was required.\n'
    cleanup_update_files
  else
    printf '\nUpdate verification failed. Rolling back Node Core application...\n' >&2
    rollback_application
    printf '✓ Node Core application restored.\n' >&2
    printf 'Kubo/IPFS and persistent data were not modified.\n' >&2
    cleanup_update_files
    exit 1
  fi
}

main "$@"
