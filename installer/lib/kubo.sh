#!/usr/bin/env bash
set -euo pipefail

detect_kubo() {
    if command -v ipfs >/dev/null 2>&1; then
        command -v ipfs
        return 0
    fi
    return 1
}

kubo_version() {
    local executable="$1"
    "$executable" version --number 2>/dev/null || "$executable" version 2>/dev/null | awk 'NR==1 {print $2}'
}
