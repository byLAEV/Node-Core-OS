#!/usr/bin/env bash
set -euo pipefail

NODE_CORE_DATA_DIR="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
NODE_CORE_APP_DIR="$NODE_CORE_DATA_DIR/app"
HASH_PAPER_ENTRY="$NODE_CORE_APP_DIR/applications/hashpaper/main.py"
NODE_CORE_BIN_DIR="$NODE_CORE_DATA_DIR/bin"
HASH_PAPER_LAUNCHER="$NODE_CORE_BIN_DIR/hashpaper"
OTS_HELPER="$NODE_CORE_APP_DIR/installer/lib/opentimestamps.sh"

require_user_installation() {
  if [[ "$(id -u)" == "0" ]]; then
    printf 'Refusing to install HashPaper as root. Run this script as your normal user without sudo.\n' >&2
    exit 1
  fi

  [[ -n "${HOME:-}" && -d "$HOME" ]] || {
    printf 'A valid user HOME directory is required.\n' >&2
    exit 1
  }

  local home_real target_real
  home_real="$(realpath -m -- "$HOME")"
  target_real="$(realpath -m -- "$NODE_CORE_DATA_DIR")"
  [[ "$target_real" == "$home_real/"* && "$target_real" != "$home_real" ]] || {
    printf 'Unsafe installation path: NODE_CORE_DATA_DIR must be inside the current user HOME.\n' >&2
    exit 1
  }

  [[ -d "$NODE_CORE_APP_DIR" && -f "$HASH_PAPER_ENTRY" && -f "$NODE_CORE_APP_DIR/applications/hashpaper/VERSION" ]] || {
    printf 'Node Core OS with a versioned HashPaper installation is not installed at: %s\n' "$NODE_CORE_APP_DIR" >&2
    printf 'Install or update Node Core OS first, then run this installer again.\n' >&2
    exit 1
  }
  local installed_version
  installed_version="$(tr -d '\r\n' < "$NODE_CORE_APP_DIR/applications/hashpaper/VERSION")"
  [[ "$installed_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
    printf 'Installed HashPaper version metadata is invalid: %s\n' "$installed_version" >&2
    exit 1
  }

  [[ ! -L "$NODE_CORE_DATA_DIR" && -d "$NODE_CORE_DATA_DIR" ]] || {
    printf 'Unsafe installation path: Node Core OS data directory must be a real directory.\n' >&2
    exit 1
  }

  [[ "$(stat -c '%u' "$NODE_CORE_DATA_DIR")" == "$(id -u)" ]] || {
    printf 'Unsafe installation path: Node Core OS data directory is not owned by the current user.\n' >&2
    exit 1
  }
}

ensure_owned_directory() {
  local directory="$1"
  if [[ -L "$directory" ]]; then
    printf 'Refusing to use a symbolic-link directory: %s\\n' "$directory" >&2
    exit 1
  fi
  mkdir -p "$directory"
  [[ -d "$directory" && ! -L "$directory" ]] || {
    printf 'Required directory is not a real directory: %s\\n' "$directory" >&2
    exit 1
  }
  [[ "$(stat -c '%u' "$directory")" == "$(id -u)" ]] || {
    printf 'Directory is not owned by the current user: %s\\n' "$directory" >&2
    exit 1
  }
  chmod 700 "$directory"
}

install_hashpaper_launcher() {
  ensure_owned_directory "$NODE_CORE_BIN_DIR"
  if [[ -L "$HASH_PAPER_LAUNCHER" ]]; then
    printf 'Refusing to overwrite a symbolic-link launcher: %s\n' "$HASH_PAPER_LAUNCHER" >&2
    exit 1
  fi

  cat > "$HASH_PAPER_LAUNCHER" <<'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail
NODE_CORE_DATA_DIR="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
export NODE_CORE_DATA_DIR
export PATH="$NODE_CORE_DATA_DIR/runtime/opentimestamps-venv/bin:$PATH"
HASH_PAPER_ENTRY="$NODE_CORE_DATA_DIR/app/applications/hashpaper/main.py"
if [[ ! -f "$HASH_PAPER_ENTRY" ]]; then
  printf 'HashPaper is missing. Update Node Core OS and try again.\n' >&2
  exit 1
fi
exec python3 "$HASH_PAPER_ENTRY" "$@"
LAUNCHER
  chmod 700 "$HASH_PAPER_LAUNCHER"
  [[ -x "$HASH_PAPER_LAUNCHER" ]]
  printf 'HashPaper launcher installed: %s\n' "$HASH_PAPER_LAUNCHER"
  printf 'Run it with: %s/hashpaper --help\n' "$NODE_CORE_BIN_DIR"
  printf 'This installer does not overwrite HashPaper documents, proofs, packages, records, identity, configuration, storage, or Kubo data.\n'
}

main() {
  require_user_installation
  [[ -f "$OTS_HELPER" ]] || { printf "OpenTimestamps installer helper is missing: %s\n" "$OTS_HELPER" >&2; exit 1; }
  source "$OTS_HELPER"
  ensure_opentimestamps_client
  ensure_owned_directory "$NODE_CORE_DATA_DIR/runtime"
  ensure_owned_directory "$NODE_CORE_DATA_DIR/hashpaper"
  ensure_owned_directory "$NODE_CORE_DATA_DIR/hashpaper/documents"
  ensure_owned_directory "$NODE_CORE_DATA_DIR/hashpaper/proofs"
  ensure_owned_directory "$NODE_CORE_DATA_DIR/hashpaper/ipfs"
  ensure_owned_directory "$NODE_CORE_DATA_DIR/hashpaper/packages"
  ensure_owned_directory "$NODE_CORE_DATA_DIR/hashpaper/records"
  install_hashpaper_launcher
}

main "$@"
