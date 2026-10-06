#!/usr/bin/env bash
set -euo pipefail

KUBO_VERSION="v0.43.1"
KUBO_BASE_URL="https://github.com/ipfs/kubo/releases/download/${KUBO_VERSION}"
KUBO_BIN_DIR="${HOME}/.node-core/bin"

kubo_asset() {
    case "$1" in
        amd64) printf '%s\n' "kubo_v0.43.1_linux-amd64.tar.gz" ;;
        arm64) printf '%s\n' "kubo_v0.43.1_linux-arm64.tar.gz" ;;
        riscv64) printf '%s\n' "kubo_v0.43.1_linux-riscv64.tar.gz" ;;
        *) return 1 ;;
    esac
}

kubo_sha256() {
    case "$1" in
        amd64) printf '%s\n' "3f2bf974ab2a3ec6d997fac7d8cb46f59983a7cddd0b55ef998e6ce379155fb2" ;;
        arm64) printf '%s\n' "e09237abadd9578d7a73dd2e2b718848b78437cb56e48cc9742b23ce9ebac829" ;;
        riscv64) printf '%s\n' "2083e4eeb50c0b95dbb61fb4e806544376bdff54037d87f3552719904f98bff4" ;;
        *) return 1 ;;
    esac
}

detect_kubo() {
    if command -v ipfs >/dev/null 2>&1; then
        command -v ipfs
        return 0
    fi
    if [ -x "${KUBO_BIN_DIR}/ipfs" ]; then
        printf '%s\n' "${KUBO_BIN_DIR}/ipfs"
        return 0
    fi
    return 1
}

install_kubo() {
    local arch="$1"
    local asset checksum tmp extract_dir
    asset="$(kubo_asset "$arch")"
    checksum="$(kubo_sha256 "$arch")"
    tmp="$(mktemp -d)"
    extract_dir="$tmp/extract"
    mkdir -p "$extract_dir" "$KUBO_BIN_DIR"

    command -v curl >/dev/null 2>&1 || { rm -rf "$tmp"; return 1; }
    curl --fail --location --silent --show-error --output "$tmp/$asset" "$KUBO_BASE_URL/$asset"
    printf '%s  %s\n' "$checksum" "$tmp/$asset" | sha256sum -c - >/dev/null
    tar -xzf "$tmp/$asset" -C "$extract_dir"
    install -m 0755 "$extract_dir/kubo/ipfs" "$KUBO_BIN_DIR/ipfs"
    rm -rf "$tmp"
    printf '%s\n' "$KUBO_BIN_DIR/ipfs"
}
