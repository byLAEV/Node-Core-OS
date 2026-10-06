#!/usr/bin/env bash
set -euo pipefail
require_linux() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    printf 'Node Core OS requires GNU/Linux.\n' >&2
    printf 'Installation aborted.\n' >&2
    return 1
  fi
}
require_bash() {
  if [[ -z "${BASH_VERSION:-}" ]]; then
    printf 'Node Core OS installer requires Bash.\n' >&2
    return 1
  fi
}
