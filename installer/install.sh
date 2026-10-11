#!/usr/bin/env bash
set -euo pipefail
INSTALLER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$INSTALLER_DIR/.." && pwd)"
source "$INSTALLER_DIR/config/defaults"
source "$INSTALLER_DIR/lib/platform.sh"
source "$INSTALLER_DIR/lib/dependencies.sh"
source "$INSTALLER_DIR/lib/network.sh"
source "$INSTALLER_DIR/lib/filesystem.sh"
source "$INSTALLER_DIR/lib/python.sh"
source "$INSTALLER_DIR/lib/kubo.sh"
source "$INSTALLER_DIR/lib/service.sh"
source "$INSTALLER_DIR/lib/verify.sh"
source "$INSTALLER_DIR/lib/opentimestamps.sh"
main() {
  printf '%s\n' 'Node Core OS installer'
  printf '%s\n' 'GNU/Linux terminal only'
  printf '%s\n\n' 'byLAEV'
  require_bash
  require_user_installation
  require_linux
  if [[ -L "$NODE_CORE_DATA_DIR/app" || ( -e "$NODE_CORE_DATA_DIR/app" && ! -d "$NODE_CORE_DATA_DIR/app" ) ]]; then
    printf 'Unsafe application path: %s is not a real directory.\n' "$NODE_CORE_DATA_DIR/app" >&2
    exit 1
  fi
  if [[ -d "$NODE_CORE_DATA_DIR/app" ]] && [[ -n "$(find "$NODE_CORE_DATA_DIR/app" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    printf 'A Node Core OS application already exists at %s.\n' "$NODE_CORE_DATA_DIR/app" >&2
    printf 'Use %s/bin/node-core-update to update an existing installation without reinstalling it.\n' "$NODE_CORE_DATA_DIR" >&2
    exit 1
  fi
  ensure_dependencies
  prepare_filesystem
  install_application "$PROJECT_ROOT"
  ensure_opentimestamps_client
  mkdir -p "$NODE_CORE_DATA_DIR/hashpaper/documents" "$NODE_CORE_DATA_DIR/hashpaper/ipfs" "$NODE_CORE_DATA_DIR/hashpaper/packages" "$NODE_CORE_DATA_DIR/hashpaper/records"
  chmod 700 "$NODE_CORE_DATA_DIR/hashpaper" "$NODE_CORE_DATA_DIR/hashpaper/documents" "$NODE_CORE_DATA_DIR/hashpaper/ipfs" "$NODE_CORE_DATA_DIR/hashpaper/packages" "$NODE_CORE_DATA_DIR/hashpaper/records"
  install_kubo
  write_config
  create_launcher
  if ! start_kubo; then
    printf '\nKubo startup failed during installation.\n' >&2
    if [[ -f "$NODE_CORE_DATA_DIR/logs/kubo.log" ]]; then
      printf '%s\n' '--- Kubo startup log ---' >&2
      cat "$NODE_CORE_DATA_DIR/logs/kubo.log" >&2
    fi
    exit 1
  fi
  if ! verify_installation; then
    printf '\nInstallation verification failed.\n' >&2
    exit 1
  fi
  enable_kubo_service
  printf '\nNode Core OS installation complete.\n'
  printf 'Launcher: %s\n' "$NODE_CORE_DATA_DIR/bin/node-core"
  printf 'Optional PATH command for the current shell:\n'
  printf '  export PATH="%s:$PATH"\n' "$NODE_CORE_DATA_DIR/bin"
  printf '\nFirst boot:\n'
  printf '  %s\n' "$NODE_CORE_DATA_DIR/bin/node-core"
}
main "$@"
