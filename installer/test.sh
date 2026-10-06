#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

. "$SCRIPT_DIR/lib/platform.sh"
assert_linux_terminal || fail "installer target rejected"
ARCH="$(detect_linux_arch)" || fail "unsupported architecture"
pass "Linux target: $ARCH"

command -v python3 >/dev/null 2>&1 || fail "python3 missing"
python3 - <<'PY'
import sys
assert sys.version_info >= (3, 10), "Python 3.10+ required"
PY
pass "Python requirement"

for f in "$SCRIPT_DIR/install.sh" "$SCRIPT_DIR/uninstall.sh" "$SCRIPT_DIR/lib/platform.sh" "$SCRIPT_DIR/lib/kubo.sh"; do
  [ -f "$f" ] || fail "missing $f"
  bash -n "$f"
done
pass "Installer shell syntax"

python3 -m unittest discover -s "$REPO_ROOT/tests" -p 'test_*.py'
pass "Node Core test suite"

printf '\nInstaller v1 static checks passed.\n'
