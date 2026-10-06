#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

[ "$(uname -s)" = "Linux" ] || fail "host is not Linux"
command -v python3 >/dev/null 2>&1 || fail "python3 is missing"
python3 - <<'PY' || exit 1
import sys
assert sys.version_info >= (3, 10), "Python 3.10+ required"
PY
pass "Linux and Python requirements"

[ -f "$REPO_ROOT/pyproject.toml" ] || fail "pyproject.toml missing"
[ -f "$REPO_ROOT/main.py" ] || fail "main.py missing"
[ -f "$SCRIPT_DIR/install.sh" ] || fail "install.sh missing"
[ -f "$SCRIPT_DIR/uninstall.sh" ] || fail "uninstall.sh missing"
[ -f "$SCRIPT_DIR/lib/kubo.sh" ] || fail "kubo.sh missing"
pass "installer files present"

bash -n "$SCRIPT_DIR/install.sh"
bash -n "$SCRIPT_DIR/uninstall.sh"
bash -n "$SCRIPT_DIR/lib/kubo.sh"
pass "installer shell syntax"

python3 -m unittest discover -s "$REPO_ROOT/tests" -p 'test_*.py'
pass "Node Core test suite"

printf '\nInstaller checks passed.\n'
