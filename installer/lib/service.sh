#!/usr/bin/env bash
set -euo pipefail

service_unit_dir() {
  printf '%s/systemd/user\n' "${XDG_CONFIG_HOME:-$HOME/.config}"
}

service_unit_path() {
  printf '%s/node-core-kubo.service\n' "$(service_unit_dir)"
}

service_backend() {
  if command -v systemctl >/dev/null 2>&1 \
    && systemctl --user show-environment >/dev/null 2>&1 \
    && systemctl --user list-unit-files >/dev/null 2>&1; then
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

write_kubo_service_unit() {
  local unit_path
  unit_path="$(service_unit_path)"
  mkdir -p "$(dirname "$unit_path")"

  cat > "$unit_path" <<EOF
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

  [[ -f "$unit_path" ]]
}

enable_kubo_service() {
  if [[ "$(service_backend)" != "systemd-user" ]]; then
    printf 'No usable user service supervisor detected; starting Kubo manually.\n'
    start_kubo
    return 0
  fi

  local unit_path
  unit_path="$(service_unit_path)"

  if ! write_kubo_service_unit; then
    printf 'Unable to create the user service unit; starting Kubo manually.\n' >&2
    start_kubo
    return 0
  fi

  if ! systemctl --user daemon-reload >/dev/null 2>&1 \
    || ! systemctl --user cat node-core-kubo.service >/dev/null 2>&1; then
    printf 'User systemd cannot load the Node Core Kubo unit; falling back to manual lifecycle.\n' >&2
    rm -f "$unit_path"
    systemctl --user daemon-reload >/dev/null 2>&1 || true
    start_kubo
    return 0
  fi

  if systemctl --user is-active node-core-kubo.service >/dev/null 2>&1; then
    systemctl --user enable node-core-kubo.service >/dev/null 2>&1 || true
    return 0
  fi

  if systemctl --user enable --now node-core-kubo.service >/dev/null 2>&1; then
    return 0
  fi

  printf 'User systemd could not start Kubo; falling back to manual lifecycle.\n' >&2
  systemctl --user disable node-core-kubo.service >/dev/null 2>&1 || true
  rm -f "$unit_path"
  systemctl --user daemon-reload >/dev/null 2>&1 || true
  start_kubo
}
