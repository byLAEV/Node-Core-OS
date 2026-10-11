#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS and HashPaper are strictly user-level software; root execution is forbidden. Run as your normal user without sudo.\\n' >&2
  exit 1
fi


# Optional source setup for the official OpenTimestamps calendar server.
# This installs source and Python dependencies only. It does not start a public
# service, configure Bitcoin Core, create a funded wallet, or expose a network port.

if [[ "$(id -u)" == "0" ]]; then
  printf 'Refusing to install the OpenTimestamps calendar server as root.\n' >&2
  exit 1
fi
[[ -n "${HOME:-}" && -d "$HOME" ]] || {
  printf 'A valid HOME directory is required.\n' >&2
  exit 1
}
for command_name in python3 tar; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'Required command not found: %s\n' "$command_name" >&2
    exit 1
  }
done
if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
  printf 'Required download command not found: curl or wget\n' >&2
  exit 1
fi

NODE_CORE_DATA_DIR="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
home_real="$(realpath -m -- "$HOME")"
target_real="$(realpath -m -- "$NODE_CORE_DATA_DIR")"
[[ "$target_real" == "$home_real/"* && "$target_real" != "$home_real" ]] || {
  printf 'Unsafe path: NODE_CORE_DATA_DIR must be inside HOME.\n' >&2
  exit 1
}
[[ ! -L "$NODE_CORE_DATA_DIR" ]] || {
  printf 'Refusing symbolic-link Node Core OS data directory.\n' >&2
  exit 1
}
mkdir -p "$NODE_CORE_DATA_DIR/optional"
[[ "$(stat -c '%u' "$NODE_CORE_DATA_DIR/optional")" == "$(id -u)" ]] || {
  printf 'Optional software directory is not owned by the current user.\n' >&2
  exit 1
}

server_dir="$NODE_CORE_DATA_DIR/optional/opentimestamps-server"
venv_dir="$NODE_CORE_DATA_DIR/runtime/opentimestamps-server-venv"
repository="https://github.com/opentimestamps/opentimestamps-server"

[[ ! -L "$server_dir" && ! -L "$venv_dir" ]] || {
  printf 'Refusing symbolic-link server source or environment path.\n' >&2
  exit 1
}
mkdir -p "$NODE_CORE_DATA_DIR/runtime"
if [[ -e "$server_dir" ]]; then
  if [[ -d "$server_dir/.git" ]] && command -v git >/dev/null 2>&1; then
    git -C "$server_dir" remote get-url origin | grep -Fx "$repository" >/dev/null || {
      printf 'Existing checkout origin does not match the official repository.\n' >&2
      exit 1
    }
  elif [[ -f "$server_dir/.node-core-official-source" ]]; then
    grep -Fx "$repository" "$server_dir/.node-core-official-source" >/dev/null || {
      printf 'Existing source marker does not match the official repository.\n' >&2
      exit 1
    }
  else
    printf 'Existing server path is not a verifiable official checkout/source; preserving it.\n' >&2
    exit 1
  fi
  printf 'Official server source already exists; not updating it automatically.\n'
else
  downloaded=0
  if command -v git >/dev/null 2>&1 && git clone --depth 1 "$repository" "$server_dir"; then
    downloaded=1
  else
    rm -rf -- "$server_dir"
    printf 'Git clone failed or is unavailable; trying official GitHub source archives.\n' >&2
  fi

  if [[ "$downloaded" != 1 ]]; then
    archive_work="$(mktemp -d "$NODE_CORE_DATA_DIR/runtime/opentimestamps-server-source.XXXXXX")"
    source_urls=(
      'https://github.com/opentimestamps/opentimestamps-server/archive/refs/heads/master.tar.gz'
      'https://codeload.github.com/opentimestamps/opentimestamps-server/tar.gz/refs/heads/master'
    )
    for source_url in "${source_urls[@]}"; do
      rm -f -- "$archive_work/source.tar.gz"
      printf 'Trying official OpenTimestamps server source: %s\n' "$source_url"
      if command -v curl >/dev/null 2>&1; then
        curl --fail --location --silent --show-error --connect-timeout 15 \
          --retry 2 --retry-delay 2 --retry-all-errors \
          --output "$archive_work/source.tar.gz" "$source_url" || continue
      else
        wget --quiet --connect-timeout=15 --tries=3 --waitretry=2 \
          --output-document="$archive_work/source.tar.gz" "$source_url" || continue
      fi
      tar -tzf "$archive_work/source.tar.gz" >/dev/null 2>&1 || {
        printf 'Invalid server source archive; trying next official source.\n' >&2
        continue
      }
      mkdir -p "$archive_work/extracted"
      tar -xzf "$archive_work/source.tar.gz" -C "$archive_work/extracted" || continue
      source_dir="$(find "$archive_work/extracted" -mindepth 1 -maxdepth 1 -type d -print -quit)"
      [[ -n "$source_dir" ]] || continue
      mv "$source_dir" "$server_dir"
      printf '%s\n' "$repository" > "$server_dir/.node-core-official-source"
      downloaded=1
      break
    done
    rm -rf -- "$archive_work"
  fi

  [[ "$downloaded" == 1 && -d "$server_dir" ]] || {
    rm -rf -- "$server_dir"
    printf 'Could not download the official OpenTimestamps server from GitHub or codeload.\n' >&2
    exit 1
  }
fi

if [[ ! -x "$venv_dir/bin/python" ]]; then
  python3 -m venv "$venv_dir"
fi
"$venv_dir/bin/python" -m pip install --upgrade pip
"$venv_dir/bin/python" -m pip install -r "$server_dir/requirements.txt"
"$venv_dir/bin/python" -m compileall -q "$server_dir/otsserver"

printf '\nOfficial OpenTimestamps server source and dependencies are installed.\n'
printf 'Source: %s\n' "$server_dir"
printf 'Python: %s\n' "$venv_dir/bin/python"
printf '\nThe server has NOT been started. Before operating it, read:\n'
printf '  %s/README.md\n' "$server_dir"
printf 'A calendar server requires a properly configured Bitcoin Core node/wallet, calendar secrets, stable URI, monitoring, and network security.\n'
printf 'Do not expose otsd directly to the public Internet; use the official deployment guidance and a suitable reverse proxy.\n'
