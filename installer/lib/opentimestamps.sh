#!/usr/bin/env bash
set -euo pipefail

# Install the official OpenTimestamps CLI in a private, user-owned virtual
# environment. This never modifies Termux's system Python or needs root.
ensure_opentimestamps_client() {
  if [[ "$(id -u)" == "0" ]]; then
    printf 'Refusing to install OpenTimestamps as root. Run Node Core OS/HashPaper as the normal user.\n' >&2
    return 1
  fi
  local runtime_dir="${NODE_CORE_DATA_DIR:-$HOME/.node-core}/runtime"
  local venv_dir="$runtime_dir/opentimestamps-venv"
  local venv_python="$venv_dir/bin/python"
  local ots_bin="$venv_dir/bin/ots"

  if [[ -L "$runtime_dir" || -L "$venv_dir" ]]; then
    printf 'Refusing to use a symbolic-link OpenTimestamps runtime path.\n' >&2
    return 1
  fi
  mkdir -p "$runtime_dir"
  if [[ "$(stat -c '%u' "$runtime_dir")" != "$(id -u)" ]]; then
    printf 'OpenTimestamps runtime directory is not owned by the current user: %s\n' "$runtime_dir" >&2
    printf 'Do not run HashPaper as root; repair this directory ownership before retrying.\n' >&2
    return 1
  fi
  if [[ -e "$venv_dir" && "$(stat -c '%u' "$venv_dir")" != "$(id -u)" ]]; then
    printf 'OpenTimestamps environment is not owned by the current user: %s\n' "$venv_dir" >&2
    printf 'The installer will not modify a root-owned environment. Inspect it and retry as the normal user.\n' >&2
    return 1
  fi

  if [[ ! -x "$venv_python" ]]; then
    printf '%s\n' 'Preparing the private OpenTimestamps Python environment...'
    if ! python3 -m venv "$venv_dir"; then
      printf '%s\n' 'Could not create the OpenTimestamps virtual environment.' >&2
      printf '%s\n' 'Install a Python 3 package with venv/pip support for your platform, then rerun the installer/updater.' >&2
      return 1
    fi
  fi

  if [[ ! -x "$ots_bin" ]] || ! "$ots_bin" --help >/dev/null 2>&1 || ! "$venv_python" -c 'import opentimestamps' >/dev/null 2>&1; then
    printf '%s\n' 'Installing the official opentimestamps-client package...'
    "$venv_python" -m pip install --upgrade pip
    "$venv_python" -m pip install --upgrade opentimestamps-client
  fi

  if [[ ! -x "$ots_bin" ]]; then
    printf 'OpenTimestamps installation did not create the expected executable: %s\n' "$ots_bin" >&2
    return 1
  fi
  if ! "$venv_python" -c 'import opentimestamps' >/dev/null 2>&1; then
    printf 'OpenTimestamps Python library failed its verification in: %s\n' "$venv_dir" >&2
    return 1
  fi
  if ! "$ots_bin" --help >/dev/null 2>&1; then
    printf 'OpenTimestamps CLI failed its verification: %s\n' "$ots_bin" >&2
    return 1
  fi

  printf '✓ OpenTimestamps CLI available: %s\n' "$ots_bin"
}
