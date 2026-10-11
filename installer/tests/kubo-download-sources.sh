#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT/installer/lib/kubo.sh"

temporary_root="$(mktemp -d)"
trap 'rm -rf "$temporary_root"' EXIT
archive="kubo_v0.43.1_linux-amd64.tar.gz"
destination="$temporary_root/$archive"
checksum="$temporary_root/$archive.sha512"
attempt_log="$temporary_root/attempts.log"

# Mock network access while exercising the real source ordering and checksum logic.
download_file() {
  local url="$1" output="$2"
  printf '%s\n' "$url" >> "$attempt_log"

  # Simulate GitHub's archive request failing, then allow dist.ipfs.tech fallback.
  if [[ "$url" == https://github.com/ipfs/kubo/releases/download/*/"$archive" ]]; then
    return 1
  fi

  if [[ "$url" == https://dist.ipfs.tech/kubo/v0.43.1/"$archive" ]]; then
    printf 'synthetic Kubo archive\n' > "$output"
    return 0
  fi

  if [[ "$url" == https://dist.ipfs.tech/kubo/v0.43.1/"$archive".sha512 ]]; then
    (cd "$temporary_root" && sha512sum "$archive" > "$output")
    return 0
  fi

  return 1
}

download_kubo_release "0.43.1" "$archive" "$destination" "$checksum"
grep -q '^https://github.com/ipfs/kubo/releases/download/v0.43.1/' "$attempt_log"
grep -q '^https://dist.ipfs.tech/kubo/v0.43.1/' "$attempt_log"
first_source="$(head -n 1 "$attempt_log")"
[[ "$first_source" == "https://github.com/ipfs/kubo/releases/download/v0.43.1/$archive" ]]
[[ -s "$destination" ]]
[[ -s "$checksum" ]]

printf 'Kubo download source-order tests: OK\n'
