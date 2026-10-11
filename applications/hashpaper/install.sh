#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
NODE_CORE_DATA_DIR="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
export NODE_CORE_DATA_DIR

if [[ "$(id -u)" == "0" ]]; then
  printf '%s\n' 'Refusing to install HashPaper dependencies as root. Run as the normal user.' >&2
  exit 1
fi

if [[ ! -f "$APP_ROOT/installer/lib/opentimestamps.sh" ]]; then
  printf 'Node Core OS installer helper was not found: %s\n' "$APP_ROOT/installer/lib/opentimestamps.sh" >&2
  printf '%s\n' 'Run this script from a complete Node Core OS source checkout.' >&2
  exit 1
fi

source "$APP_ROOT/installer/lib/opentimestamps.sh"
ensure_opentimestamps_client

printf '\nHashPaper OpenTimestamps dependency is ready.\n'
printf 'Executable: %s\n' "$NODE_CORE_DATA_DIR/runtime/opentimestamps-venv/bin/ots"
printf 'Launch HashPaper with: %s/bin/hashpaper\n' "$NODE_CORE_DATA_DIR"
