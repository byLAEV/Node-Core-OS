#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEMP_ROOT"' EXIT

# The Termux wrapper must reject a non-Termux shell before package operations.
unset TERMUX_VERSION PREFIX || true
if bash "$REPOSITORY_ROOT/installer/termux-install.sh" 2>"$TEMP_ROOT/non-termux.err"; then
  printf 'FAIL: Termux installer accepted a non-Termux shell.\n' >&2
  exit 1
fi
grep -q 'must be run inside Termux' "$TEMP_ROOT/non-termux.err"

# Source helper functions so dependency selection can be tested without
# installing Android packages on the CI runner.
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

# Force native cryptography to be unavailable so package selection is
# deterministic even if the CI host already has cryptography installed.
source "$REPOSITORY_ROOT/installer/termux-install.sh"
packages="$(termux_missing_packages)"
grep -qx 'python-cryptography' <<<"$packages"
grep -qx 'kubo' <<<"$packages"
termux_install_dependencies
grep -q '^install -y python-cryptography kubo$' "$TERMUX_PKG_LOG"

printf 'Termux installer platform and dependency-selection tests passed.\n'
