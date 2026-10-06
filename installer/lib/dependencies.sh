#!/usr/bin/env bash
set -euo pipefail
python_version_ok() {
  python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
}
check_dependencies() {
  local missing=0 command_name
  for command_name in bash python3 tar sha512sum mkdir cp rm mktemp uname awk; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
      printf 'Missing required command: %s\n' "$command_name" >&2
      missing=1
    fi
  done
  if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    printf 'Missing required download command: curl or wget\n' >&2
    missing=1
  fi
  return "$missing"
}
check_python() {
  if ! python_version_ok; then
    printf 'Python 3.10 or newer is required.\n' >&2
    return 1
  fi
}
