#!/usr/bin/env bash
set -euo pipefail
node_core_compatibility_preflight() {
  local source_root="$1"
  local mode="${2:-install}"
  local python_executable="${3:-python3}"
  local manifest="$source_root/compatibility/manifest.json"
  [[ -f "$manifest" ]] || { printf 'Node Core compatibility manifest is missing: %s\n' "$manifest" >&2; return 1; }
  command -v "$python_executable" >/dev/null 2>&1 || { printf 'Python interpreter unavailable: %s\n' "$python_executable" >&2; return 1; }
  printf '\n%s\n' '--- Node Core Terminal Compatibility Preflight ---'
  if PYTHONPATH="$source_root${PYTHONPATH:+:$PYTHONPATH}" NODE_CORE_ACTIVE_SHELL=bash \
      "$python_executable" -m node_core.compatibility --manifest "$manifest" --mode "$mode"; then
    printf '%s\n\n' 'Terminal compatibility preflight passed.'
    return 0
  else
    local result=$?
    printf 'Terminal compatibility preflight rejected this environment (exit %s).\n' "$result" >&2
    printf '%s\n' 'No Node Core application files were changed by this preflight.' >&2
    return "$result"
  fi
}
