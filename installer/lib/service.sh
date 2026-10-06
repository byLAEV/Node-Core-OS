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
