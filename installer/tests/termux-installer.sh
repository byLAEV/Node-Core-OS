#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEMP_ROOT"' EXIT

# The legacy command is only an alias to the unified Linux terminal installer.
grep -Fq 'exec bash "$INSTALLER_DIR/install.sh" "$@"' "$REPOSITORY_ROOT/installer/termux-install.sh"

# Simulate Termux detection on a Linux CI host without installing packages.
export TERMUX_VERSION="test-termux"
export PREFIX="$TEMP_ROOT/prefix"
mkdir -p "$PREFIX/bin" "$TEMP_ROOT/fake-bin"
export TERMUX_PKG_LOG="$TEMP_ROOT/pkg.log"
cat > "$TEMP_ROOT/fake-bin/pkg" <<'PKG'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$TERMUX_PKG_LOG"
PKG
chmod +x "$TEMP_ROOT/fake-bin/pkg"

REAL_PYTHON3="$(command -v python3)"
cat > "$TEMP_ROOT/fake-bin/python3" <<'PYTHON'
#!/usr/bin/env bash
if [[ "${1:-}" == "-c" && "${2:-}" == *"import cryptography"* ]]; then
  exit 1
fi
exec "$REAL_PYTHON3" "$@"
PYTHON
chmod +x "$TEMP_ROOT/fake-bin/python3"
export REAL_PYTHON3
export PATH="$TEMP_ROOT/fake-bin:$PATH"

source "$REPOSITORY_ROOT/installer/config/defaults"
source "$REPOSITORY_ROOT/installer/lib/platform.sh"
source "$REPOSITORY_ROOT/installer/lib/dependencies.sh"

node_core_is_termux
[[ "$(node_core_platform_name)" == *"Termux-compatible"* ]]
linux_terminal_install_missing_dependencies
grep -q '^install -y python-cryptography kubo$' "$TERMUX_PKG_LOG"

# Outside Termux, the same dependency function must not invoke pkg.
unset TERMUX_VERSION PREFIX
if node_core_is_termux; then
  printf 'FAIL: generic Linux was misdetected as Termux.\n' >&2
  exit 1
fi
printf 'Unified Linux terminal and Termux compatibility tests passed.\n'
