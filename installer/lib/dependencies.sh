#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS installer helpers cannot run as root. Use the normal user account without sudo.\\n' >&2
  return 1 2>/dev/null || exit 1
fi


python_version_ok() {
  python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
}

check_dependencies() {
  local missing=0 command_name
  for command_name in bash python3 tar sha512sum mkdir cp rm mktemp uname awk realpath stat id; do
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

ensure_dependencies() {
  if ! check_dependencies; then
    printf 'Missing installer dependencies. Install them in your Linux terminal and run the installer again.\n' >&2
    printf 'Node Core OS does not install host packages and never requires root or sudo.\n' >&2
    return 1
  fi
  check_python
}

check_python() {
  if ! python_version_ok; then
    printf 'Python 3.10 or newer is required.\n' >&2
    return 1
  fi
}
