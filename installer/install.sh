#!/usr/bin/env bash
set -euo pipefail
INSTALLER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$INSTALLER_DIR/.." && pwd)"
source "$INSTALLER_DIR/config/defaults"
source "$INSTALLER_DIR/lib/platform.sh"
source "$INSTALLER_DIR/lib/dependencies.sh"
source "$INSTALLER_DIR/lib/filesystem.sh"
source "$INSTALLER_DIR/lib/python.sh"
source "$INSTALLER_DIR/lib/kubo.sh"
source "$INSTALLER_DIR/lib/service.sh"
source "$INSTALLER_DIR/lib/verify.sh"
main() {
  printf '%s\n' 'Node Core OS installer'
  printf '%s\n' 'GNU/Linux terminal only'
  printf '%s\n\n' 'byLAEV'
  require_bash
  require_linux
  ensure_dependencies
  prepare_filesystem
  install_application "$PROJECT_ROOT"
  install_kubo
  start_kubo
  write_config
  create_launcher
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
