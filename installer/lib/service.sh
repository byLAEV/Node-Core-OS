#!/usr/bin/env bash
set -euo pipefail

service_backend() {
  if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    printf 'systemd-user\n'
  else
    printf 'manual\n'
  fi
}

service_status() {
  case "$(service_backend)" in
    systemd-user)
      systemctl --user is-active node-core-kubo.service >/dev/null 2>&1
      ;;
    manual)
      return 1
      ;;
  esac
}

enable_kubo_service() {
  if [[ "$(service_backend)" != "systemd-user" ]]; then
    printf 'No user service supervisor detected; manual Kubo lifecycle retained.\n'
    return 0
  fi
  local unit_dir="$HOME/.config/systemd/user"
  mkdir -p "$unit_dir"
  cat > "$unit_dir/node-core-kubo.service" <<EOF
[Unit]
Description=Node Core OS Kubo daemon
After=network-online.target

[Service]
Type=simple
Environment=IPFS_PATH=$NODE_CORE_DATA_DIR/ipfs
ExecStart=$NODE_CORE_DATA_DIR/bin/ipfs daemon
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now node-core-kubo.service
}
