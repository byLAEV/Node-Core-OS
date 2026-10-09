#!/usr/bin/env bash
set -euo pipefail

require_user_installation() {
  local uid home_real target_real
  uid="$(id -u)"
  if [[ "$uid" == "0" ]]; then
    printf 'Refusing to install, update, or remove Node Core OS as root. Run it as your normal user without sudo.\n' >&2
    return 1
  fi

  [[ -n "${HOME:-}" && -d "$HOME" ]] || {
    printf 'A valid user HOME directory is required.\n' >&2
    return 1
  }

  home_real="$(realpath -m -- "$HOME")"
  target_real="$(realpath -m -- "$NODE_CORE_DATA_DIR")"
  [[ "$target_real" == "$home_real/"* && "$target_real" != "$home_real" ]] || {
    printf 'Unsafe installation path: NODE_CORE_DATA_DIR must be inside the current user HOME.\n' >&2
    printf 'Current target: %s\n' "$target_real" >&2
    return 1
  }

  if [[ -e "$NODE_CORE_DATA_DIR" || -L "$NODE_CORE_DATA_DIR" ]]; then
    [[ ! -L "$NODE_CORE_DATA_DIR" && -d "$NODE_CORE_DATA_DIR" ]] || {
      printf 'Unsafe installation path: target must be a real directory, not a symbolic link.\n' >&2
      return 1
    }
    [[ "$(stat -c '%u' "$NODE_CORE_DATA_DIR")" == "$uid" ]] || {
      printf 'Unsafe installation path: target directory is not owned by the current user.\n' >&2
      return 1
    }
  fi
}

require_linux() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    printf 'Node Core OS requires GNU/Linux.\n' >&2
    printf 'Installation aborted.\n' >&2
    return 1
  fi
}
require_bash() {
  if [[ -z "${BASH_VERSION:-}" ]]; then
    printf 'Node Core OS installer requires Bash.\n' >&2
    return 1
  fi
}
