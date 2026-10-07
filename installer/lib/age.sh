#!/usr/bin/env bash
set -euo pipefail

NODE_CORE_AGE_VERSION="${NODE_CORE_AGE_VERSION:-1.3.2}"

age_asset() {
  case "$(uname -m)" in
    x86_64|amd64) printf 'linux-amd64\\n' ;;
    aarch64|arm64) printf 'linux-arm64\\n' ;;
    *) printf 'Unsupported Linux architecture for age: %s\n' "$(uname -m)" >&2; return 1 ;;
  esac
}

age_sha256() {
  case "$1" in
    linux-amd64) printf '%s\\n' 'cbe24006683f8eb669266162894b9a522a1af52f2665fbc63a4bb032ed26ac10' ;;
    linux-arm64) printf '%s\\n' '6b8dc4333c53a5a57c9e5834e3a48f92605d7154014cd07269ff3327db5d37f4' ;;
    *) return 1 ;;
  esac
}

install_age() {
  local version="$NODE_CORE_AGE_VERSION" asset archive work_dir expected actual age_binary
  asset="$(age_asset)"
  archive="age-v${version}-${asset}.tar.gz"
  work_dir="$(mktemp -d)"
  expected="$(age_sha256 "$asset")"
  printf 'Downloading age %s (%s)...\n' "$version" "$asset"
  download_file "https://github.com/FiloSottile/age/releases/download/v${version}/${archive}" "$work_dir/$archive"
  actual="$(sha256sum "$work_dir/$archive" | awk '{print $1}')"
  if [[ "$actual" != "$expected" ]]; then
    printf 'age checksum verification failed.\nExpected: %s\nActual:   %s\n' "$expected" "$actual" >&2
    rm -rf "$work_dir"; return 1
  fi
  tar -xzf "$work_dir/$archive" -C "$work_dir"
  age_binary="$(find "$work_dir" -type f -name age -perm -u+x -print -quit)"
  [[ -n "$age_binary" ]] || { rm -rf "$work_dir"; return 1; }
  cp "$age_binary" "$NODE_CORE_DATA_DIR/bin/age"
  chmod +x "$NODE_CORE_DATA_DIR/bin/age"
  rm -rf "$work_dir"
  [[ "$("$NODE_CORE_DATA_DIR/bin/age" --version)" == "v${version}" ]]
}
