#!/usr/bin/env bash
set -euo pipefail

# Install the official OpenTimestamps CLI in a private, user-owned virtual
# environment. This never modifies Termux's system Python or needs root.
ensure_opentimestamps_client() {
  local runtime_dir="${NODE_CORE_DATA_DIR:-$HOME/.node-core}/runtime"
  local venv_dir="$runtime_dir/opentimestamps-venv"
  local venv_python="$venv_dir/bin/python"
  local ots_bin="$venv_dir/bin/ots"

  mkdir -p "$runtime_dir"

  if [[ ! -x "$venv_python" ]]; then
    printf '%s\n' 'Preparing the private OpenTimestamps Python environment...'
    if ! python3 -m venv "$venv_dir"; then
      printf '%s\n' 'Could not create the OpenTimestamps virtual environment.' >&2
      printf '%s\n' 'Install a Python 3 package with venv/pip support for your platform, then rerun the installer/updater.' >&2
      return 1
    fi
  fi

  if [[ ! -x "$ots_bin" ]] || ! "$ots_bin" --help >/dev/null 2>&1; then
    printf '%s\n' 'Installing the official opentimestamps-client package...'
    "$venv_python" -m pip install --upgrade pip
    "$venv_python" -m pip install --upgrade opentimestamps-client
  fi

  if [[ ! -x "$ots_bin" ]]; then
    printf 'OpenTimestamps installation did not create the expected executable: %s\n' "$ots_bin" >&2
    return 1
  fi
  if ! "$ots_bin" --help >/dev/null 2>&1; then
    printf 'OpenTimestamps CLI failed its verification: %s\n' "$ots_bin" >&2
    return 1
  fi

  printf '✓ OpenTimestamps CLI available: %s\n' "$ots_bin"
}
