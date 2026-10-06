#!/usr/bin/env bash
set -euo pipefail

detect_linux_arch() {
    case "$(uname -m)" in
        x86_64|amd64) printf '%s\n' "amd64" ;;
        aarch64|arm64) printf '%s\n' "arm64" ;;
        riscv64) printf '%s\n' "riscv64" ;;
        *) return 1 ;;
    esac
}

assert_linux_terminal() {
    [ "$(uname -s)" = "Linux" ] || {
        printf '%s\n' "Node Core OS Installer supports Linux terminals only." >&2
        return 1
    }
    if [ "$(uname -o 2>/dev/null || true)" = "Android" ] || [ -n "${TERMUX_VERSION:-}" ]; then
        printf '%s\n' "Android/Termux is outside the supported Linux terminal target." >&2
        return 1
    fi
}
