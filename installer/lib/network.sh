#!/usr/bin/env bash
set -euo pipefail

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

download_file() {
  local url="$1" destination="$2"
  if command -v curl >/dev/null 2>&1; then
    # Downloads have no artificial connection or transfer deadline.
    # Retries handle transport errors while slow healthy transfers remain valid.
    curl --fail --location --silent --show-error \
      --connect-timeout 10 \
      --retry 3 --retry-delay 2 --retry-all-errors \
      --continue-at - --output "$destination" "$url"
  elif command -v wget >/dev/null 2>&1; then
    # Do not impose a download timeout. Resume only against the same source.
    wget --quiet --tries=4 --waitretry=2 --connect-timeout=10 \
      --continue --output-document="$destination" "$url"
  else
    printf 'No supported download client found (curl or wget required).\n' >&2
    return 127
  fi
}
