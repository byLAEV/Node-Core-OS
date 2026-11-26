#!/usr/bin/env bash
set -euo pipefail

HASH_PAPER_REPOSITORY="${HASH_PAPER_REPOSITORY:-byLAEV/Node-Core-OS}"
HASH_PAPER_BRANCH="${HASH_PAPER_BRANCH:-main}"
NODE_CORE_DATA_DIR="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
NODE_CORE_APP_DIR="$NODE_CORE_DATA_DIR/app"
HASH_PAPER_TARGET="$NODE_CORE_APP_DIR/applications/hashpaper"
HASH_PAPER_RUNTIME_DIR="$NODE_CORE_DATA_DIR/runtime"
HASH_PAPER_UPDATE_DIR="$HASH_PAPER_RUNTIME_DIR/hashpaper-update"
HASH_PAPER_LOCK_DIR="$HASH_PAPER_RUNTIME_DIR/hashpaper-update.lock"

require_user_installation() {
  if [[ "$(id -u)" == "0" ]]; then
    printf 'Refusing to update HashPaper as root. Run this updater as your normal user without sudo.\n' >&2
    exit 1
  fi

  local home_real target_real
  [[ -n "${HOME:-}" && -d "$HOME" ]] || {
    printf 'A valid user HOME directory is required.\n' >&2
    exit 1
  }
  home_real="$(realpath -m -- "$HOME")"
  target_real="$(realpath -m -- "$NODE_CORE_DATA_DIR")"
  [[ "$target_real" == "$home_real/"* && "$target_real" != "$home_real" ]] || {
    printf 'Unsafe update path: NODE_CORE_DATA_DIR must be inside the current user HOME.\n' >&2
    exit 1
  }
  [[ ! -L "$NODE_CORE_DATA_DIR" && -d "$NODE_CORE_DATA_DIR" ]] || {
    printf 'Node Core OS data directory is missing or is a symbolic link.\n' >&2
    exit 1
  }
  [[ "$(stat -c '%u' "$NODE_CORE_DATA_DIR")" == "$(id -u)" ]] || {
    printf 'Node Core OS data directory is not owned by the current user.\n' >&2
    exit 1
  }
  [[ -d "$NODE_CORE_APP_DIR" && -d "$HASH_PAPER_TARGET" ]] || {
    printf 'Existing Node Core OS and HashPaper installation not found at %s.\n' "$HASH_PAPER_TARGET" >&2
    exit 1
  }
  [[ -f "$NODE_CORE_APP_DIR/main.py" && -f "$NODE_CORE_APP_DIR/node_core/runtime.py" ]] || {
    printf 'Node Core OS application files are incomplete; refusing a HashPaper-only update.\n' >&2
    exit 1
  }
}

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
    printf 'Neither curl nor wget is available.\n' >&2
    return 1
  fi
}

cleanup_working_files() {
  rm -rf "$HASH_PAPER_UPDATE_DIR"
}

latest_commit() {
  local response="$HASH_PAPER_UPDATE_DIR/latest-commit.json"
  download_file "https://api.github.com/repos/$HASH_PAPER_REPOSITORY/commits/$HASH_PAPER_BRANCH" "$response"
  python3 - "$response" <<'PY'
import json
import re
import sys
data = json.loads(open(sys.argv[1], encoding="utf-8").read())
sha = data.get("sha")
if not isinstance(sha, str) or re.fullmatch(r"[0-9a-fA-F]{40}", sha) is None:
    raise SystemExit("GitHub returned invalid commit metadata; refusing to update.")
print(sha.lower())
PY
}

verify_hashpaper_tree() {
  local root="$1"
  [[ -f "$root/VERSION" && -f "$root/main.py" && -f "$root/hashpaper/cli.py" && -d "$root/tests" ]] || {
    printf 'Downloaded HashPaper source is incomplete.\n' >&2
    return 1
  }
  local version
  version="$(tr -d '\r\n' < "$root/VERSION")"
  [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
    printf 'Downloaded HashPaper version is invalid: %s\n' "$version" >&2
    return 1
  }
  python3 -m compileall -q "$root" || return 1
  (cd "$NODE_CORE_APP_DIR" && PYTHONPATH="$root/../.." python3 -m unittest discover -s "$root/tests" -p 'test_*.py' -v)
}

main() {
  require_user_installation
  mkdir -p "$HASH_PAPER_RUNTIME_DIR"
  [[ ! -L "$HASH_PAPER_RUNTIME_DIR" && -d "$HASH_PAPER_RUNTIME_DIR" ]] || {
    printf 'Unsafe Node Core OS runtime directory.\n' >&2
    exit 1
  }

  if ! mkdir "$HASH_PAPER_LOCK_DIR" 2>/dev/null; then
    printf 'Another HashPaper update may be running, or a previous update was interrupted.\n' >&2
    printf 'Lock directory: %s\n' "$HASH_PAPER_LOCK_DIR" >&2
    printf 'Inspect the installation before removing a stale lock.\n' >&2
    exit 1
  fi
  trap 'rmdir "$HASH_PAPER_LOCK_DIR" 2>/dev/null || true' EXIT

  if [[ -e "$HASH_PAPER_UPDATE_DIR" || -L "$HASH_PAPER_UPDATE_DIR" ]]; then
    printf 'Previous HashPaper update recovery files exist; refusing to overwrite them.\n' >&2
    printf 'Recovery directory: %s\n' "$HASH_PAPER_UPDATE_DIR" >&2
    exit 1
  fi
  mkdir -p "$HASH_PAPER_UPDATE_DIR/source" "$HASH_PAPER_UPDATE_DIR/backup"

  local current_version remote_commit local_commit archive extract source staged
  current_version="$(cat "$HASH_PAPER_TARGET/VERSION" 2>/dev/null || printf 'unknown')"
  remote_commit="$(latest_commit)"
  archive="$HASH_PAPER_UPDATE_DIR/source.tar.gz"
  extract="$HASH_PAPER_UPDATE_DIR/source"
  download_file "https://github.com/$HASH_PAPER_REPOSITORY/archive/$remote_commit.tar.gz" "$archive"
  tar -xzf "$archive" -C "$extract"

  source="$(find "$extract" -mindepth 1 -maxdepth 1 -type d -print -quit)"
  [[ -n "$source" && -d "$source/applications/hashpaper" ]] || {
    printf 'Release archive does not contain applications/hashpaper.\n' >&2
    exit 1
  }
  staged="$source/applications/hashpaper"
  verify_hashpaper_tree "$staged"

  local_version="$(tr -d '\r\n' < "$staged/VERSION")"
  printf 'Installed HashPaper version: %s\n' "$current_version"
  printf 'Available HashPaper version: %s\n' "$local_version"
  printf 'Source commit: %s\n' "$remote_commit"

  if [[ "$current_version" == "$local_version" ]]; then
    printf 'HashPaper is already at version %s. No application files changed.\n' "$current_version"
    cleanup_working_files
    return 0
  fi

  printf '\nThis operation updates only applications/hashpaper.\n'
  printf 'Node Core OS core, Kubo binary/repository, configuration, identity, local storage,\n'
  printf 'HashPaper documents, .ots proofs, packages, and publication records are preserved.\n\n'
  read -r -p 'Update HashPaper only? [Y/n] ' answer
  case "${answer:-y}" in
    y|Y|yes|YES) ;;
    *) printf 'Update cancelled.\n'; cleanup_working_files; return 0 ;;
  esac

  cp -R "$HASH_PAPER_TARGET/." "$HASH_PAPER_UPDATE_DIR/backup/"
  if ! rm -rf "$HASH_PAPER_TARGET" || ! mkdir -p "$HASH_PAPER_TARGET" || ! cp -R "$staged/." "$HASH_PAPER_TARGET/"; then
    printf 'Failed while installing HashPaper files; restoring backup.\n' >&2
    rm -rf "$HASH_PAPER_TARGET"
    mkdir -p "$HASH_PAPER_TARGET"
    cp -R "$HASH_PAPER_UPDATE_DIR/backup/." "$HASH_PAPER_TARGET/"
    exit 1
  fi

  if ! verify_hashpaper_tree "$HASH_PAPER_TARGET"; then
    printf 'Updated HashPaper verification failed; restoring previous version.\n' >&2
    rm -rf "$HASH_PAPER_TARGET"
    mkdir -p "$HASH_PAPER_TARGET"
    cp -R "$HASH_PAPER_UPDATE_DIR/backup/." "$HASH_PAPER_TARGET/"
    verify_hashpaper_tree "$HASH_PAPER_TARGET" || {
      printf 'ERROR: HashPaper rollback verification failed. Backup retained at %s\n' "$HASH_PAPER_UPDATE_DIR/backup" >&2
      exit 1
    }
    cleanup_working_files
    exit 1
  fi

  cleanup_working_files
  printf '\n✓ HashPaper updated successfully to version %s.\n' "$local_version"
  printf '✓ Node Core OS core was not replaced.\n'
  printf '✓ Kubo/IPFS and all persistent user data were not replaced.\n'
}

main "$@"
