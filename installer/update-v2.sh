#!/usr/bin/env bash
set -euo pipefail

# Node Core OS Update Package V2
# Updates only the Node Core application. It does not install, replace,
# configure, initialize, or remove Kubo/IPFS.
NODE_CORE_REPOSITORY="${NODE_CORE_REPOSITORY:-https://github.com/byLAEV/Node-Core-OS}"
NODE_CORE_BRANCH="${NODE_CORE_BRANCH:-main}"
NODE_CORE_DATA_DIR="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
NODE_CORE_APP_DIR="$NODE_CORE_DATA_DIR/app"
NODE_CORE_RUNTIME_DIR="$NODE_CORE_DATA_DIR/runtime"
NODE_CORE_UPDATE_DIR="$NODE_CORE_RUNTIME_DIR/update-v2"
NODE_CORE_COMMIT_FILE="$NODE_CORE_RUNTIME_DIR/node-core-commit"
NODE_CORE_VERSION_FILE="$NODE_CORE_RUNTIME_DIR/node-core-version"

download_file() {
  local url="$1" destination="$2"
  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --silent --show-error \
      --connect-timeout 15 --retry 3 --retry-delay 2 --retry-all-errors \
      --output "$destination" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget --quiet --connect-timeout=15 --tries=4 --waitretry=2 \
      --output-document="$destination" "$url"
  else
    printf '%s\n' 'Missing dependency: curl or wget is required.' >&2
    return 1
  fi
}

require_installation() {
  [[ -d "$NODE_CORE_APP_DIR" ]] || {
    printf 'Node Core OS installation not found: %s\n' "$NODE_CORE_DATA_DIR" >&2
    printf '%s\n' 'Install Node Core OS first; this package is for updates only.' >&2
    exit 1
  }
  [[ -f "$NODE_CORE_APP_DIR/main.py" && -d "$NODE_CORE_APP_DIR/node_core" ]] || {
    printf '%s\n' 'The existing Node Core application is incomplete. Aborting safely.' >&2
    exit 1
  }
  command -v python3 >/dev/null 2>&1 || {
    printf '%s\n' 'Python 3 is required to verify the updated application.' >&2
    exit 1
  }
  command -v tar >/dev/null 2>&1 || {
    printf '%s\n' 'tar is required to unpack the update.' >&2
    exit 1
  }
}

latest_commit() {
  local response="$NODE_CORE_UPDATE_DIR/latest-commit.json"
  download_file \
    "https://api.github.com/repos/byLAEV/Node-Core-OS/commits/$NODE_CORE_BRANCH" \
    "$response"
  python3 - "$response" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
sha = data.get("sha")
if not isinstance(sha, str) or len(sha) != 40:
    raise SystemExit("GitHub response did not contain a valid commit SHA.")
print(sha)
PY
}

prepare_source() {
  local commit="$1"
  local archive="$NODE_CORE_UPDATE_DIR/source.tar.gz"
  local extract="$NODE_CORE_UPDATE_DIR/source"
  rm -rf "$extract"
  mkdir -p "$extract"
  download_file "$NODE_CORE_REPOSITORY/archive/$commit.tar.gz" "$archive"
  tar -xzf "$archive" -C "$extract"
  find "$extract" -mindepth 1 -maxdepth 1 -type d -print -quit
}

verify_source() {
  local source="$1"
  [[ -f "$source/main.py" && -d "$source/node_core" ]] || {
    printf '%s\n' 'Downloaded source is missing required Node Core files.' >&2
    return 1
  }
  python3 -m compileall -q "$source/main.py" "$source/node_core"
}

backup_application() {
  local backup="$NODE_CORE_UPDATE_DIR/app-backup"
  rm -rf "$backup"
  cp -R "$NODE_CORE_APP_DIR" "$backup"
}

restore_application() {
  local backup="$NODE_CORE_UPDATE_DIR/app-backup"
  [[ -d "$backup" ]] || {
    printf '%s\n' 'Rollback backup is missing; manual recovery may be required.' >&2
    return 1
  }
  rm -rf "$NODE_CORE_APP_DIR"
  cp -R "$backup" "$NODE_CORE_APP_DIR"
}

cleanup_update() {
  rm -rf "$NODE_CORE_UPDATE_DIR/source" "$NODE_CORE_UPDATE_DIR/app-backup"
  rm -f "$NODE_CORE_UPDATE_DIR/source.tar.gz" "$NODE_CORE_UPDATE_DIR/latest-commit.json"
}

main() {
  printf '%s\n' 'Node Core OS Update Package V2'
  printf '%s\n' 'Kubo/IPFS is excluded from this update package.'
  printf '\n'

  require_installation
  mkdir -p "$NODE_CORE_RUNTIME_DIR" "$NODE_CORE_UPDATE_DIR"

  local remote_commit local_commit source
  remote_commit="$(latest_commit)"
  local_commit=''
  [[ ! -f "$NODE_CORE_COMMIT_FILE" ]] || local_commit="$(cat "$NODE_CORE_COMMIT_FILE")"

  printf 'Installed commit: %s\n' "${local_commit:-unknown}"
  printf 'Available commit: %s\n' "$remote_commit"
  printf 'Package version: 2.0.0\n\n'

  if [[ "$local_commit" == "$remote_commit" ]]; then
    printf '%s\n' 'Node Core OS application is already up to date.'
    cleanup_update
    return 0
  fi

  source="$(prepare_source "$remote_commit")"
  [[ -n "$source" ]] || {
    printf '%s\n' 'Could not locate extracted source directory.' >&2
    cleanup_update
    exit 1
  }
  verify_source "$source"

  printf '%s\n' 'This update replaces only the Node Core application directory.'
  printf '%s\n' 'It does not modify config.json, storage/, ipfs/, Kubo binaries, or Kubo services.'
  printf '%s\n' 'A temporary backup of the current application will be created.'
  read -r -p 'Apply this update? [Y/n] ' answer
  case "${answer:-y}" in
    y|Y|yes|YES) ;;
    *) printf '%s\n' 'Update cancelled.'; cleanup_update; return 0 ;;
  esac

  backup_application
  if {
    rm -rf "$NODE_CORE_APP_DIR"
    mkdir -p "$NODE_CORE_APP_DIR"
    cp -R "$source"/. "$NODE_CORE_APP_DIR"/
    rm -rf "$NODE_CORE_APP_DIR/.git"
    python3 -m compileall -q "$NODE_CORE_APP_DIR/main.py" "$NODE_CORE_APP_DIR/node_core"
  }; then
    printf '%s\n' "$remote_commit" > "$NODE_CORE_COMMIT_FILE"
    printf '%s\n' '2.0.0' > "$NODE_CORE_VERSION_FILE"
    printf '\n%s\n' 'Update completed and Python compilation passed.'
    printf '%s\n' 'Kubo/IPFS and persistent data were not intentionally modified.'
    cleanup_update
  else
    printf '\n%s\n' 'Update verification failed; restoring the previous application.' >&2
    restore_application
    cleanup_update
    exit 1
  fi
}

main "$@"
