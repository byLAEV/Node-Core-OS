#!/usr/bin/env bash
set -euo pipefail
REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEMP_ROOT"' EXIT
# Legacy installer entry must fail closed without invoking package managers or touching user data.
export TERMUX_VERSION="test-termux"
export PREFIX="$TEMP_ROOT/prefix"
mkdir -p "$PREFIX/bin"
set +e
output="$(bash "$REPOSITORY_ROOT/installer/termux-install.sh" 2>&1)"
status=$?
set -e
[[ "$status" -ne 0 ]]
grep -q 'GNU/Linux only' <<<"$output"
grep -q 'use Lindesk' <<<"$output"
[[ ! -e "$HOME/.node-core" || -d "$HOME/.node-core" ]]
printf 'PASS: legacy Termux entry point rejects Android/Termux safely.\n'
