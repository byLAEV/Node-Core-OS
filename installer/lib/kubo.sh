#!/usr/bin/env bash
set -euo pipefail

kubo_asset() {
  case "$(uname -m)" in
    x86_64|amd64) printf 'linux-amd64\n' ;;
    aarch64|arm64) printf 'linux-arm64\n' ;;
    *) printf 'Unsupported Linux architecture: %s\n' "$(uname -m)" >&2; return 1 ;;
  esac
}

download_kubo_release() {
  local version="$1" archive="$2" destination="$3" checksum="$4"
  local primary="https://dist.ipfs.tech/kubo/v\${version}"
  local fallback="https://github.com/ipfs/kubo/releases/download/v\${version}"
  local source source_dir

  for source in "$primary" "$fallback"; do
    source_dir="$(mktemp -d "\${destination}.source.XXXXXX")"
    printf 'Trying Kubo source: %s\n' "$source"
    printf 'Transfer timeout: none (slow connections allowed).\n'

    if download_file "$source/$archive" "$source_dir/$archive" &&
       download_file "$source/$archive.sha512" "$source_dir/$archive.sha512"; then
      if (cd "$source_dir" && sha512sum --check "$archive.sha512"); then
        cp "$source_dir/$archive" "$destination"
        cp "$source_dir/$archive.sha512" "$checksum"
        rm -rf "$source_dir"
        printf 'Kubo download verified from %s\n' "$source"
        return 0
      fi
      printf 'Checksum verification failed for %s\n' "$source" >&2
    else
      printf 'Kubo download failed from %s\n' "$source" >&2
    fi

    rm -rf "$source_dir"
  done

  printf 'Unable to download and verify Kubo %s from any configured source.\n' "$version" >&2
  return 1
}

install_kubo() {
  local version="$NODE_CORE_KUBO_VERSION" asset archive work_dir installed_version
  asset="$(kubo_asset)"
  archive="kubo_v\${version}_\${asset}.tar.gz"
  work_dir="$(mktemp -d)"
  printf 'Downloading Kubo %s (%s)...\n' "$version" "$asset"

  if ! download_kubo_release "$version" "$archive" \
      "$work_dir/$archive" "$work_dir/$archive.sha512"; then
    rm -rf "$work_dir"
    return 1
  fi

  tar -xzf "$work_dir/$archive" -C "$work_dir"
  cp "$work_dir/kubo/ipfs" "$NODE_CORE_DATA_DIR/bin/ipfs"
  chmod +x "$NODE_CORE_DATA_DIR/bin/ipfs"
  installed_version="$("$NODE_CORE_DATA_DIR/bin/ipfs" version | awk '{print $3}')"
  rm -rf "$work_dir"

  if [[ "$installed_version" != "$version" ]]; then
    printf 'Kubo version verification failed: expected %s, got %s\n' "$version" "$installed_version" >&2
    return 1
  fi

  export IPFS_PATH="$NODE_CORE_DATA_DIR/ipfs"
  if [[ ! -f "$IPFS_PATH/config" ]]; then
    "$NODE_CORE_DATA_DIR/bin/ipfs" init
    "$NODE_CORE_DATA_DIR/bin/ipfs" config profile apply unixfs-v1-2025
  fi
  "$NODE_CORE_DATA_DIR/bin/ipfs" config Addresses.API "$NODE_CORE_KUBO_API_MULTIADDR"
  "$NODE_CORE_DATA_DIR/bin/ipfs" config Addresses.Gateway "$NODE_CORE_KUBO_GATEWAY_MULTIADDR"
}

start_kubo() {
  export IPFS_PATH="$NODE_CORE_DATA_DIR/ipfs"
  if http_post "$NODE_CORE_KUBO_API/api/v0/id" >/dev/null 2>&1; then
    return 0
  fi

  nohup "$NODE_CORE_DATA_DIR/bin/ipfs" daemon >"$NODE_CORE_DATA_DIR/logs/kubo.log" 2>&1 &
  local pid="$!"
  printf '%s\n' "$pid" > "$NODE_CORE_DATA_DIR/runtime/kubo.pid"

  local attempt
  for attempt in {1..40}; do
    if http_post "$NODE_CORE_KUBO_API/api/v0/id" >/dev/null 2>&1; then
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
