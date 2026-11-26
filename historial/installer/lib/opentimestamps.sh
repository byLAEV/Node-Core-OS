#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS installer helpers cannot run as root. Use the normal user account without sudo.\\n' >&2
  return 1 2>/dev/null || exit 1
fi


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
    local installed=0 source_work='' source_url
    printf '%s\n' 'Installing the official OpenTimestamps client (pinned release 0.7.2)...'

    # Primary source: the official PyPI package. Keep pip inside this venv.
    if "$venv_python" -m pip install --upgrade --retries 3 --timeout 20 \
      --index-url https://pypi.org/simple 'opentimestamps-client==0.7.2'; then
      installed=1
    else
      printf '%s\n' 'PyPI installation failed; trying the official GitHub source archive.' >&2
    fi

    # Fallbacks are official upstream GitHub archive endpoints for the same tag.
    if [[ "$installed" != 1 ]]; then
      source_work="$(mktemp -d "$runtime_dir/opentimestamps-source.XXXXXX")" || {
        printf 'Could not create a temporary OpenTimestamps source directory.\n' >&2
        return 1
      }
      local source_urls=(
        'https://github.com/opentimestamps/opentimestamps-client/archive/refs/tags/opentimestamps-client-v0.7.2.tar.gz'
        'https://codeload.github.com/opentimestamps/opentimestamps-client/tar.gz/refs/tags/opentimestamps-client-v0.7.2'
      )
      for source_url in "${source_urls[@]}"; do
        rm -f -- "$source_work/source.tar.gz"
        printf 'Trying OpenTimestamps source: %s\n' "$source_url"
        if command -v curl >/dev/null 2>&1; then
          if ! curl --fail --location --silent --show-error --connect-timeout 15 \
            --retry 2 --retry-delay 2 --retry-all-errors \
            --output "$source_work/source.tar.gz" "$source_url"; then
            continue
          fi
        elif command -v wget >/dev/null 2>&1; then
          if ! wget --quiet --connect-timeout=15 --tries=3 --waitretry=2 \
            --output-document="$source_work/source.tar.gz" "$source_url"; then
            continue
          fi
        else
          printf 'Neither curl nor wget is available for source fallback.\n' >&2
          rm -rf -- "$source_work"
          return 1
        fi

        if ! tar -tzf "$source_work/source.tar.gz" >/dev/null 2>&1; then
          printf 'OpenTimestamps source archive is invalid; trying the next official source.\n' >&2
          continue
        fi
        mkdir -p "$source_work/extracted"
        if ! tar -xzf "$source_work/source.tar.gz" -C "$source_work/extracted"; then
          rm -rf -- "$source_work/extracted"
          continue
        fi
        local source_dir
        source_dir="$(find "$source_work/extracted" -mindepth 1 -maxdepth 1 -type d -print -quit)"
        if [[ -n "$source_dir" ]] && "$venv_python" -m pip install --upgrade --retries 3 --timeout 20 "$source_dir"; then
          installed=1
          break
        fi
        rm -rf -- "$source_work/extracted"
      done
      rm -rf -- "$source_work"
    fi

    if [[ "$installed" != 1 ]]; then
      printf 'Could not install OpenTimestamps client from PyPI or either official GitHub source.\n' >&2
      return 1
    fi
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
