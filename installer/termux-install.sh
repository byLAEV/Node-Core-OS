#!/usr/bin/env bash
set -euo pipefail

# Backward-compatible command name. Node Core OS has one installer for Linux
# terminal environments; Termux compatibility is detected inside install.sh.
INSTALLER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$INSTALLER_DIR/install.sh" "$@"
