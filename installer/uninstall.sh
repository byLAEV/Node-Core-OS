#!/usr/bin/env bash
set -euo pipefail
INSTALLER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$INSTALLER_DIR/config/defaults"

validate_uninstall_target() {
  local target="$NODE_CORE_DATA_DIR" canonical_target canonical_home parent
  [[ "$target" = /* ]] || { printf 'Unsafe uninstall path: must be absolute.\n' >&2; return 1; }
  canonical_target="$(realpath -m -- "$target")"
  canonical_home="$(realpath -m -- "$HOME")"
  [[ "$canonical_target" != "/" ]] || { printf 'Unsafe uninstall path: refusing to remove a filesystem root.\n' >&2; return 1; }
  [[ "$canonical_target" != "$canonical_home" ]] || { printf 'Unsafe uninstall path: refusing to remove HOME.\n' >&2; return 1; }
  if [[ -e "$target" || -L "$target" ]]; then
    [[ ! -L "$target" ]] || { printf 'Unsafe uninstall path: target is a symbolic link.\n' >&2; return 1; }
    [[ -d "$target" ]] || { printf 'Unsafe uninstall path: target is not a directory.\n' >&2; return 1; }
    [[ "$(stat -c '%u' "$target")" = "$(id -u)" ]] || { printf 'Unsafe uninstall path: target is not owned by the current user.\n' >&2; return 1; }
  else
    parent="$(dirname -- "$canonical_target")"
    [[ -d "$parent" ]] || { printf 'Unsafe uninstall path: parent directory does not exist.\n' >&2; return 1; }
    [[ ! -L "$parent" ]] || { printf 'Unsafe uninstall path: parent directory is a symbolic link.\n' >&2; return 1; }
    [[ "$(stat -c '%u' "$parent")" = "$(id -u)" ]] || { printf 'Unsafe uninstall path: parent is not owned by the current user.\n' >&2; return 1; }
  fi
}
printf 'Node Core OS uninstall\n'
printf 'This removes: %s\n' "$NODE_CORE_DATA_DIR"
printf 'It also removes the local Kubo repository and Node Core data stored there.\n'
validate_uninstall_target
printf 'Type REMOVE to continue: '
read -r confirmation
if [[ "$confirmation" != "REMOVE" ]]; then
  printf 'Uninstall cancelled.\n'
  exit 0
fi

unit_path="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/node-core-kubo.service"
if command -v systemctl >/dev/null 2>&1 \
  && systemctl --user show-environment >/dev/null 2>&1 \
  && [[ -f "$unit_path" ]]; then
  systemctl --user disable --now node-core-kubo.service >/dev/null 2>&1 || true
  rm -f "$unit_path"
  systemctl --user daemon-reload >/dev/null 2>&1 || true
fi

if [[ -x "$NODE_CORE_DATA_DIR/bin/ipfs" ]]; then
  export IPFS_PATH="$NODE_CORE_DATA_DIR/ipfs"
  "$NODE_CORE_DATA_DIR/bin/ipfs" shutdown >/dev/null 2>&1 || true
fi
if [[ -f "$NODE_CORE_DATA_DIR/runtime/kubo.pid" ]]; then
  pid="$(cat "$NODE_CORE_DATA_DIR/runtime/kubo.pid" 2>/dev/null || true)"
  if [[ "$pid" =~ ^[0-9]+$ ]]; then kill "$pid" >/dev/null 2>&1 || true; fi
fi
rm -rf -- "$NODE_CORE_DATA_DIR"
printf 'Node Core OS installation removed.\n'
