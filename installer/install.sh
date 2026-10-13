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
  # HashPaper is maintained as a separate application; do not bundle it in Node Core OS.
  rm -rf "$NODE_CORE_DATA_DIR/app/applications/hashpaper"
  rm -f "$NODE_CORE_DATA_DIR/app/installer/hashpaper-install.sh" "$NODE_CORE_DATA_DIR/app/installer/hashpaper-update.sh"
  rm -f "$NODE_CORE_DATA_DIR/app/installer/tests/hashpaper-install.sh" "$NODE_CORE_DATA_DIR/app/installer/tests/hashpaper-update.sh"
  rm -f "$NODE_CORE_DATA_DIR/app/docs/HASHPAPER.md" "$NODE_CORE_DATA_DIR/app/docs/HASHPAPER-FUNCTIONAL-MANIFEST.md"
  rm -f "$NODE_CORE_DATA_DIR/app/tests/test_hashpaper_storage_layout.py"
  rm -f "$NODE_CORE_DATA_DIR/app/.github/workflows/hashpaper-opentimestamps-live.yml" "$NODE_CORE_DATA_DIR/app/.github/workflows/hashpaper-python-matrix.yml"
  [[ -f "$NODE_CORE_DATA_DIR/app/VERSION" ]] || {
    printf 'Installed Node Core OS version file is missing.\n' >&2
    exit 1
  }
  [[ -f "$NODE_CORE_DATA_DIR/app/applications/p2p_contracts/main.py" ]] || {
    printf 'Installed Node Core P2P Contracts entry point is missing.\n' >&2
    exit 1
  }
  [[ -f "$NODE_CORE_DATA_DIR/app/applications/p2p_contracts/VERSION" ]] || {
    printf 'Installed Node Core P2P Contracts version file is missing.\n' >&2
    exit 1
  }
  [[ -f "$NODE_CORE_DATA_DIR/app/applications/p2p_contracts/p2p_contracts/cli.py" ]] || {
    printf 'Installed Node Core P2P Contracts CLI is missing.\n' >&2
    exit 1
  }
  [[ -d "$NODE_CORE_DATA_DIR/app/applications/p2p_contracts/tests" ]] || {
    printf 'Installed Node Core P2P Contracts tests are missing.\n' >&2
    exit 1
  }
  python3 - "$NODE_CORE_DATA_DIR/app/applications/p2p_contracts/VERSION" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
version = path.read_text(encoding="utf-8").strip()
if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None:
    raise SystemExit(f"Invalid Node Core P2P Contracts version in {path}: {version!r}")
if version != "1.0.0":
    raise SystemExit(f"Expected Node Core P2P Contracts 1.0.0, found {version}")
print("Installed Node Core P2P Contracts version:", version)
PY
  python3 -m compileall -q "$NODE_CORE_DATA_DIR/app/applications/p2p_contracts"
  (cd "$NODE_CORE_DATA_DIR/app" && python3 -m unittest applications.p2p_contracts.tests.test_service applications.p2p_contracts.tests.test_propagation -v)
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
