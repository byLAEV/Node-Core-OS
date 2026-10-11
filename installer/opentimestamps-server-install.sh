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
for command_name in git python3; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'Required command not found: %s\n' "$command_name" >&2
    exit 1
  }
done

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
  [[ -d "$server_dir/.git" ]] || {
    printf 'Existing server path is not a Git checkout; preserving it.\n' >&2
    exit 1
  }
  git -C "$server_dir" remote get-url origin | grep -Fx "$repository" >/dev/null || {
    printf 'Existing checkout origin does not match the official repository.\n' >&2
    exit 1
  }
  printf 'Official server checkout already exists; not updating it automatically.\n'
else
  git clone --depth 1 "$repository" "$server_dir"
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
