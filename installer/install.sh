#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS and HashPaper are strictly user-level software; root execution is forbidden. Run as your normal user without sudo.\n' >&2
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
  [[ -f "$NODE_CORE_DATA_DIR/app/VERSION" ]] || {
    printf 'Installed Node Core OS version file is missing.\n' >&2
    exit 1
  }
  [[ -f "$NODE_CORE_DATA_DIR/app/applications/hashpaper/VERSION" ]] || {
    printf 'Installed HashPaper version file is missing.\n' >&2
    exit 1
  }
  python3 - "$NODE_CORE_DATA_DIR/app/VERSION" "$NODE_CORE_DATA_DIR/app/applications/hashpaper/VERSION" <<'PY'
import re
import sys
from pathlib import Path

for value in sys.argv[1:]:
    path = Path(value)
    version = path.read_text(encoding="utf-8").strip()
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None:
        raise SystemExit(f"Invalid application version in {path}: {version!r}")
print("Installed Node Core OS version:", Path(sys.argv[1]).read_text(encoding="utf-8").strip())
print("Installed HashPaper version:", Path(sys.argv[2]).read_text(encoding="utf-8").strip())
PY
  [[ -f "$NODE_CORE_DATA_DIR/app/applications/p2p_contracts/main.py" ]] || {
    printf 'Installed P2P Contracts entry point is missing.\n' >&2
    exit 1
  }
  [[ -f "$NODE_CORE_DATA_DIR/app/applications/p2p_contracts/p2p_contracts/cli.py" ]] || {
    printf 'Installed P2P Contracts CLI is missing.\n' >&2
    exit 1
  }
  [[ -d "$NODE_CORE_DATA_DIR/app/applications/p2p_contracts/tests" ]] || {
    printf 'Installed P2P Contracts tests are missing.\n' >&2
    exit 1
  }
  python3 -m compileall -q "$NODE_CORE_DATA_DIR/app/applications/hashpaper" "$NODE_CORE_DATA_DIR/app/applications/p2p_contracts"
  (cd "$NODE_CORE_DATA_DIR/app" && python3 -m unittest discover -s applications/hashpaper/tests -p 'test_*.py' -v)
  (cd "$NODE_CORE_DATA_DIR/app" && python3 -m unittest applications.p2p_contracts.tests.test_service applications.p2p_contracts.tests.test_propagation -v)
  mkdir -p "$NODE_CORE_DATA_DIR/hashpaper/documents" "$NODE_CORE_DATA_DIR/hashpaper/proofs" "$NODE_CORE_DATA_DIR/hashpaper/ipfs" "$NODE_CORE_DATA_DIR/hashpaper/packages" "$NODE_CORE_DATA_DIR/hashpaper/records"
  chmod 700 "$NODE_CORE_DATA_DIR/hashpaper" "$NODE_CORE_DATA_DIR/hashpaper/documents" "$NODE_CORE_DATA_DIR/hashpaper/proofs" "$NODE_CORE_DATA_DIR/hashpaper/ipfs" "$NODE_CORE_DATA_DIR/hashpaper/packages" "$NODE_CORE_DATA_DIR/hashpaper/records"
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
