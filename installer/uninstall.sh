#!/usr/bin/env bash
set -euo pipefail
INSTALLER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$INSTALLER_DIR/config/defaults"
printf 'Node Core OS uninstall\n'
printf 'This removes: %s\n' "$NODE_CORE_DATA_DIR"
printf 'It also removes the local Kubo repository and Node Core data stored there.\n'
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
rm -rf "$NODE_CORE_DATA_DIR"
printf 'Node Core OS installation removed.\n'
