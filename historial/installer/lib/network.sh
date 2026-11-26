#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS installer helpers cannot run as root. Use the normal user account without sudo.\\n' >&2
  return 1 2>/dev/null || exit 1
fi


http_post() {
  local url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl --fail --silent --show-error --max-time 3 -X POST "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget --quiet --timeout=3 --tries=1 --method=POST --output-document=- "$url"
  else
    return 127
  fi
}
