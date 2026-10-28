#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS is strictly user-level software; root execution is forbidden. Run as your normal user without sudo.\n' >&2
  exit 1
fi

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
  ensure_python_environment "$NODE_CORE_DATA_DIR/app/requirements.txt"

  # Validate the cryptographic engine inside the exact virtual environment used
  # by the installed application, then create this node's persistent identity.
  if ! "$NODE_CORE_DATA_DIR/runtime/node-core-venv/bin/python" -c 'import cryptography; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; print("Verified cryptographic engine:", cryptography.__version__, "| Ed25519: available")'; then
    printf 'Cryptographic engine verification failed; refusing to finish installation.\n' >&2
    exit 1
  fi
  (
    cd "$NODE_CORE_DATA_DIR/app"
    "$NODE_CORE_DATA_DIR/runtime/node-core-venv/bin/python" -m unittest tests.test_node_identity -v
    NODE_CORE_DATA_DIR="$NODE_CORE_DATA_DIR" "$NODE_CORE_DATA_DIR/runtime/node-core-venv/bin/python" -c 'import os; from pathlib import Path; from node_core.identity.node_identity import NodeIdentityStore; store = NodeIdentityStore(Path(os.environ["NODE_CORE_DATA_DIR"])); identity = store.initialize(); assert store.load()["node_id"] == identity["node_id"]; print("Initialized persistent Ed25519 node identity:", identity["node_id"])'
  )
  # HashPaper and P2P Contracts are suspended and must not ship as active Node Core OS applications.
  rm -rf "$NODE_CORE_DATA_DIR/app/applications/hashpaper" "$NODE_CORE_DATA_DIR/app/applications/p2p_contracts"
  rm -f "$NODE_CORE_DATA_DIR/app/installer/hashpaper-install.sh" "$NODE_CORE_DATA_DIR/app/installer/hashpaper-update.sh"
  rm -f "$NODE_CORE_DATA_DIR/app/installer/opentimestamps-server-install.sh"
  rm -f "$NODE_CORE_DATA_DIR/app/installer/tests/hashpaper-install.sh" "$NODE_CORE_DATA_DIR/app/installer/tests/hashpaper-update.sh"
  rm -f "$NODE_CORE_DATA_DIR/app/docs/HASHPAPER.md" "$NODE_CORE_DATA_DIR/app/docs/HASHPAPER-FUNCTIONAL-MANIFEST.md"
  rm -f "$NODE_CORE_DATA_DIR/app/tests/test_hashpaper_storage_layout.py"
  rm -f "$NODE_CORE_DATA_DIR/app/.github/workflows/hashpaper-opentimestamps-live.yml" "$NODE_CORE_DATA_DIR/app/.github/workflows/hashpaper-python-matrix.yml"
  rm -f "$NODE_CORE_DATA_DIR/app/docs/P2P-CONTRACTS-APPLICATION-STRUCTURE.md" \
    "$NODE_CORE_DATA_DIR/app/docs/P2P-CONTRACTS-BTC-REQUEST-PROTOTYPE.md" \
    "$NODE_CORE_DATA_DIR/app/docs/P2P-CONTRACTS-DEVELOPMENT-PLAN.md" \
    "$NODE_CORE_DATA_DIR/app/docs/P2P-CONTRACTS-PUBLIC-MANIFEST-PROTOCOL.md" \
    "$NODE_CORE_DATA_DIR/app/docs/P2P-CONTRACTS-SCHEMAS.md" \
    "$NODE_CORE_DATA_DIR/app/docs/P2P-CONTRACTS-TECHNICAL-AUDIT.md"
  rm -f "$NODE_CORE_DATA_DIR/app/.github/workflows/three-independent-ubuntu-p2p-contracts.yml" \
    "$NODE_CORE_DATA_DIR/app/.github/workflows/three-independent-ubuntu-p2p-e2e.yml"
  [[ -f "$NODE_CORE_DATA_DIR/app/VERSION" ]] || {
    printf 'Installed Node Core OS version file is missing.\n' >&2
    exit 1
  }
  # P2P Contracts is suspended: no application-specific checks or tests run during installation.
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
