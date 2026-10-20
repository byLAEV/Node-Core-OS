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
export TERMUX_INSTALLER_LIBRARY_ONLY=1
mkdir -p "$PREFIX/bin" "$TEMP_ROOT/fake-bin"
export TERMUX_PKG_LOG="$TEMP_ROOT/pkg.log"
cat > "$TEMP_ROOT/fake-bin/pkg" <<'PKG'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$TERMUX_PKG_LOG"
PKG
chmod +x "$TEMP_ROOT/fake-bin/pkg"
export PATH="$TEMP_ROOT/fake-bin:$PATH"

# On the CI host, standard shell dependencies exist, but the Termux ipfs
# executable does not. The wrapper should select the Kubo package.
source "$REPOSITORY_ROOT/installer/termux-install.sh"
packages="$(termux_missing_packages)"
grep -qx 'kubo' <<<"$packages"
termux_install_dependencies
grep -q '^install -y kubo$' "$TERMUX_PKG_LOG"

printf 'Termux installer platform and dependency-selection tests passed.\n'
