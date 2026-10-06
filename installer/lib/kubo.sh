#!/usr/bin/env bash
set -euo pipefail
kubo_asset() {
  case "$(uname -m)" in
    x86_64|amd64) printf 'linux-amd64\n' ;;
    aarch64|arm64) printf 'linux-arm64\n' ;;
    *) printf 'Unsupported Linux architecture: %s\n' "$(uname -m)" >&2; return 1 ;;
  esac
}
download_file() {
  local url="$1" destination="$2"
  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --silent --show-error --connect-timeout 15 --max-time 120 --retry 3 --retry-delay 2 --retry-all-errors --output "$destination" "$url"
  else
    wget --quiet --timeout=15 --tries=4 --waitretry=2 --output-document="$destination" "$url"
  fi
}
download_kubo_release() {
  local version="$1" archive="$2" destination="$3" checksum="$4"
  local primary="https://dist.ipfs.tech/kubo/v${version}"
  local fallback="https://github.com/ipfs/kubo/releases/download/v${version}"
  local source
  for source in "$primary" "$fallback"; do
    rm -f "$destination" "$checksum"
    printf 'Trying Kubo source: %s\n' "$source"
    if download_file "$source/$archive" "$destination" && download_file "$source/$archive.sha512" "$checksum"; then
      if (cd "$(dirname "$destination")" && sha512sum --check "$(basename "$checksum")"); then
        printf 'Kubo download verified from %s\n' "$source"
        return 0
      fi
      printf 'Checksum verification failed for %s\n' "$source" >&2
    else
      printf 'Kubo download failed from %s\n' "$source" >&2
    fi
  done
  printf 'Unable to download and verify Kubo %s from any configured source.\n' "$version" >&2
  return 1
}
install_kubo() {
  local version="$NODE_CORE_KUBO_VERSION" asset archive base_url work_dir installed_version
  asset="$(kubo_asset)"
  archive="kubo_v${version}_${asset}.tar.gz"
  base_url="https://dist.ipfs.tech/kubo/v$version"
  work_dir="$(mktemp -d)"
  trap 'rm -rf "$work_dir"' RETURN
  printf 'Downloading Kubo %s (%s)...\n' "$version" "$asset"
  download_kubo_release "$version" "$archive" "$work_dir/$archive" "$work_dir/$archive.sha512"
  tar -xzf "$work_dir/$archive" -C "$work_dir"
  cp "$work_dir/kubo/ipfs" "$NODE_CORE_DATA_DIR/bin/ipfs"
  chmod +x "$NODE_CORE_DATA_DIR/bin/ipfs"
  installed_version="$("$NODE_CORE_DATA_DIR/bin/ipfs" version | awk '{print $3}')"
  if [[ "$installed_version" != "$version" ]]; then
    printf 'Kubo version verification failed: expected %s, got %s\n' "$version" "$installed_version" >&2
    return 1
  fi
  export IPFS_PATH="$NODE_CORE_DATA_DIR/ipfs"
  if [[ ! -f "$IPFS_PATH/config" ]]; then
    "$NODE_CORE_DATA_DIR/bin/ipfs" init
    "$NODE_CORE_DATA_DIR/bin/ipfs" config profile apply unixfs-v1-2025
  fi
  "$NODE_CORE_DATA_DIR/bin/ipfs" config Addresses.API "$NODE_CORE_KUBO_API"
  "$NODE_CORE_DATA_DIR/bin/ipfs" config Addresses.Gateway "$NODE_CORE_KUBO_GATEWAY"
}

start_kubo() {
  export IPFS_PATH="$NODE_CORE_DATA_DIR/ipfs"
  if curl --fail --silent --show-error --max-time 2 -X POST "$NODE_CORE_KUBO_API/api/v0/id" >/dev/null 2>&1; then
    return 0
  fi

  nohup "$NODE_CORE_DATA_DIR/bin/ipfs" daemon >"$NODE_CORE_DATA_DIR/logs/kubo.log" 2>&1 &
  local pid="$!"
  printf '%s\n' "$pid" > "$NODE_CORE_DATA_DIR/runtime/kubo.pid"

  local attempt
  for attempt in {1..40}; do
    if curl --fail --silent --show-error --max-time 2 -X POST "$NODE_CORE_KUBO_API/api/v0/id" >/dev/null 2>&1; then
      return 0
    fi
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      printf 'Kubo daemon exited during startup. See %s.\n' "$NODE_CORE_DATA_DIR/logs/kubo.log" >&2
      return 1
    fi
    sleep 0.25
  done

  printf 'Kubo API did not become ready. See %s.\n' "$NODE_CORE_DATA_DIR/logs/kubo.log" >&2
  return 1
}
