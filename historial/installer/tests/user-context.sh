#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../lib/platform.sh
source "$REPOSITORY_ROOT/installer/lib/platform.sh"

temporary_root="$(mktemp -d)"
trap 'rm -rf "$temporary_root"' EXIT
export HOME="$temporary_root/home"
mkdir -p "$HOME"
NODE_CORE_DATA_DIR="$HOME/.node-core"

require_user_installation

# Simulate root and verify that the guard rejects it before touching files.
id() {
  printf '0\n'
}
if require_user_installation 2>/dev/null; then
  printf 'FAIL: root execution was accepted.\n' >&2
  exit 1
fi
unset -f id

# Paths outside HOME must be rejected.
NODE_CORE_DATA_DIR="$temporary_root/outside"
if require_user_installation 2>/dev/null; then
  printf 'FAIL: installation path outside HOME was accepted.\n' >&2
  exit 1
fi

printf 'User-context guards passed.\n'
