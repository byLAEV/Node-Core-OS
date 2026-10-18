#!/usr/bin/env bash
set -euo pipefail

# This is the only installer entry point that may install Termux host packages.
# The generic GNU/Linux installer remains package-manager agnostic.

termux_require_environment() {
  if [[ -z "${TERMUX_VERSION:-}" || -z "${PREFIX:-}" || ! -d "${PREFIX:-}" ]]; then
    printf 'This installer must be run inside Termux on Android.\n' >&2
    return 1
  fi
  if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "aarch64" ]]; then
    printf 'This Termux installer currently supports Android aarch64 only.\n' >&2
    return 1
  fi
  if [[ "$(id -u)" == "0" ]]; then
    printf 'Do not run the Termux installer as root.\n' >&2
    return 1
  fi
  command -v pkg >/dev/null 2>&1 || {
    printf 'Termux package manager (pkg) is not available.\n' >&2
    return 1
  }
}

termux_add_package_once() {
  local package="$1" existing
  for existing in "${TERMUX_REQUIRED_PACKAGES[@]}"; do
    [[ "$existing" == "$package" ]] && return 0
  done
  TERMUX_REQUIRED_PACKAGES+=("$package")
}

termux_missing_packages() {
  local command_name
  TERMUX_REQUIRED_PACKAGES=()

  command -v bash >/dev/null 2>&1 || termux_add_package_once bash
  command -v python3 >/dev/null 2>&1 || termux_add_package_once python
  command -v tar >/dev/null 2>&1 || termux_add_package_once tar
  command -v curl >/dev/null 2>&1 || termux_add_package_once curl
  command -v grep >/dev/null 2>&1 || termux_add_package_once grep
  command -v sed >/dev/null 2>&1 || termux_add_package_once sed
  command -v find >/dev/null 2>&1 || termux_add_package_once findutils
  command -v awk >/dev/null 2>&1 || termux_add_package_once gawk

  for command_name in sha512sum realpath stat mkdir cp rm mktemp uname id; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
      termux_add_package_once coreutils
      break
    fi
  done

  [[ -x "$PREFIX/bin/ipfs" ]] || termux_add_package_once kubo
  printf '%s\n' "${TERMUX_REQUIRED_PACKAGES[@]}"
}

termux_install_dependencies() {
  local -a packages=()
  mapfile -t packages < <(termux_missing_packages)
  if (("${#packages[@]}" == 0)); then
    printf 'Termux dependencies are already available.\n'
    return 0
  fi
  printf 'Installing missing Termux packages: %s\n' "${packages[*]}"
  pkg install -y "${packages[@]}"
}

termux_check_dependencies() {
  local command_name
  for command_name in bash python3 tar curl grep sed find awk sha512sum realpath stat mkdir cp rm mktemp uname id; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
      printf 'Required Termux command is still missing after package preparation: %s\n' "$command_name" >&2
      return 1
    fi
  done
  [[ -x "$PREFIX/bin/ipfs" ]] || {
    printf 'Termux Kubo executable is missing: %s/bin/ipfs\n' "$PREFIX" >&2
    printf 'Install the Termux kubo package and retry.\n' >&2
    return 1
  }
}

termux_main() {
  local project_root data_dir
  termux_require_environment

  project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
  source "$project_root/installer/config/defaults"
  data_dir="$NODE_CORE_DATA_DIR"

  termux_install_dependencies
  termux_check_dependencies

  if [[ -f "$data_dir/app/main.py" && -d "$data_dir/app/node_core" ]]; then
    printf 'Existing Node Core OS installation detected.\n'
    printf 'Delegating to the existing updater; it will request confirmation and preserve persistent data.\n'
    if [[ -x "$data_dir/bin/node-core-update" ]]; then
      exec "$data_dir/bin/node-core-update" "$@"
    elif [[ -f "$data_dir/app/installer/update.sh" ]]; then
      exec bash "$data_dir/app/installer/update.sh" "$@"
    else
      printf 'Existing application found but no updater is available. Nothing was changed.\n' >&2
      return 1
    fi
  fi

  if [[ -e "$data_dir/config.json" || -f "$data_dir/ipfs/config" || -n "$(find "$data_dir/storage" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null || true)" ]]; then
    printf 'Persistent Node Core data exists without a complete application at %s.\n' "$data_dir" >&2
    printf 'Refusing a fresh install to avoid replacing existing configuration or data. Review the installation manually.\n' >&2
    return 1
  fi

  exec bash "$project_root/installer/install.sh" "$@"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  termux_main "$@"
fi
