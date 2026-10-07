#!/usr/bin/env bash
set -euo pipefail

NODE_CORE_AGE_VERSION="\${NODE_CORE_AGE_VERSION:-1.3.2}"

age_asset() {
  case "$(uname -m)" in
    x86_64|amd64) printf 'linux-amd64\n' ;;
    aarch64|arm64) printf 'linux-arm64\n' ;;
    *) printf 'Unsupported Linux architecture for age: %s\n' "$(uname -m)" >&2; return 1 ;;
  esac
}

age_sha256() {
  case "$1" in
    linux-amd64) printf '%s\n' 'cbe24006683f8eb669266162894b9a522a1af52f2665fbc63a4bb032ed26ac10' ;;
    linux-arm64) printf '%s\n' '6b8dc4333c53a5a57c9e5834e3a48f92605d7154014cd07269ff3327db5d37f4' ;;
    *) return 1 ;;
  esac
}

age_download_url() {
  local source="$1" version="$2" asset="$3" archive="$4"
  case "$source" in
    filippo)
      case "$asset" in
        linux-amd64) printf 'https://dl.filippo.io/age/v%s?for=linux/amd64\n' "$version" ;;
        linux-arm64) printf 'https://dl.filippo.io/age/v%s?for=linux/arm64\n' "$version" ;;
        *) return 1 ;;
      esac
      ;;
    github)
      printf 'https://github.com/FiloSottile/age/releases/download/v%s/%s\n' "$version" "$archive"
      ;;
    *) return 1 ;;
  esac
}

install_age() {
  local version="$NODE_CORE_AGE_VERSION" asset archive work_dir expected actual age_binary
  local source url source_dir
  asset="$(age_asset)"
  archive="age-v\${version}-\${asset}.tar.gz"
  work_dir="$(mktemp -d)"
  expected="$(age_sha256 "$asset")"
  printf 'Downloading age %s (%s)...\n' "$version" "$asset"

  for source in filippo github; do
    source_dir="$(mktemp -d "\${work_dir}/source.XXXXXX")"
    url="$(age_download_url "$source" "$version" "$asset" "$archive")"
    printf 'Trying age source: %s\n' "$url"
    printf 'Transfer timeout: none (slow connections allowed).\n'

    if download_file "$url" "$source_dir/$archive"; then
      actual="$(sha256sum "$source_dir/$archive" | awk '{print $1}')"
      if [[ "$actual" == "$expected" ]]; then
        tar -xzf "$source_dir/$archive" -C "$source_dir"
        age_binary="$(find "$source_dir" -type f -name age -perm -u+x -print -quit)"
        if [[ -n "$age_binary" ]]; then
          cp "$age_binary" "$NODE_CORE_DATA_DIR/bin/age"
          chmod +x "$NODE_CORE_DATA_DIR/bin/age"
          if [[ "$("$NODE_CORE_DATA_DIR/bin/age" --version)" == "v\${version}" ]]; then
            rm -rf "$work_dir"
            printf 'age download verified from %s\n' "$source"
            return 0
          fi
          printf 'age version verification failed for %s\n' "$source" >&2
        else
          printf 'age binary not found in archive from %s\n' "$source" >&2
        fi
      else
        printf 'age checksum verification failed for %s\nExpected: %s\nActual:   %s\n' \
          "$source" "$expected" "$actual" >&2
      fi
    else
      printf 'age download failed from %s\n' "$source" >&2
    fi
    rm -rf "$source_dir"
  done

  rm -rf "$work_dir"
  printf 'Unable to download and verify age %s from any configured official source.\n' "$version" >&2
  return 1
}
