#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -eq 0 ]]; then
  printf 'Refusing root execution. Run this installer as the normal LinDesk user without sudo.\n' >&2
  exit 1
fi
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_DIR="$SCRIPT_DIR/source"
[[ -f "$SOURCE_DIR/installer/install.sh" && -f "$SOURCE_DIR/VERSION" ]] || {
  printf 'The bundled Node Core OS source tree is incomplete.\n' >&2
  exit 1
}
[[ "$(cat "$SOURCE_DIR/VERSION")" == "1.5.6" ]] || {
  printf 'Source version mismatch; refusing installation.\n' >&2
  exit 1
}
[[ "$(uname -s)" == "Linux" ]] || { printf 'Linux is required.\n' >&2; exit 1; }
case "$(uname -m)" in aarch64|arm64) ;; *) printf 'This LinDesk package targets ARM64; detected %s.\n' "$(uname -m)" >&2; exit 1;; esac
[[ -n "${HOME:-}" && -d "$HOME" ]] || { printf 'A valid HOME directory is required.\n' >&2; exit 1; }

printf '\n=== NODE CORE OS 1.5.6 / LINDESK PREFLIGHT ===\n'
printf 'Timestamp: '; date -Is
printf 'User: '; id
printf 'Architecture: '; uname -m
printf 'Kernel: '; uname -sr
printf 'Distribution: '
if [[ -r /etc/os-release ]]; then . /etc/os-release; printf '%s %s\n' "${PRETTY_NAME:-unknown}" "${VERSION_ID:-}"; else printf 'unknown\n'; fi
printf '\n=== MEMORY ===\n'
if [[ -r /proc/meminfo ]]; then awk '/^(MemTotal|MemAvailable|SwapTotal|SwapFree):/ {print}' /proc/meminfo; else printf '/proc/meminfo unavailable\n'; fi
printf '\n=== CGROUP MEMORY LIMITS ===\n'
for f in /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory/memory.limit_in_bytes; do
  if [[ -r "$f" ]]; then printf '%s: ' "$f"; cat "$f"; fi
done
printf '\n=== VIRTUALIZATION / CONTAINER HINTS ===\n'
if command -v systemd-detect-virt >/dev/null 2>&1; then systemd-detect-virt || true; else printf 'systemd-detect-virt unavailable; checking kernel hints\n'; fi
if [[ -r /proc/1/cgroup ]]; then sed -n '1,12p' /proc/1/cgroup; fi
printf '\n=== HOME STORAGE ===\n'
df -h "$HOME"
printf '\n=== REQUIRED COMMANDS ===\n'
missing=0
for cmd in bash python3 tar sha512sum mkdir cp rm mktemp uname awk realpath stat id find grep sed nohup; do
  if command -v "$cmd" >/dev/null 2>&1; then printf 'OK   %s\n' "$cmd"; else printf 'MISS %s\n' "$cmd"; missing=1; fi
done
if command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1; then printf 'OK   curl/wget\n'; else printf 'MISS curl/wget\n'; missing=1; fi
printf '\n=== PYTHON ===\n'
python3 --version
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10 or newer is required.")
print("Python version requirement: PASS")
try:
    import venv
    print("Python venv module: available")
except Exception as exc:
    print(f"Python venv module: unavailable ({exc})")
PY
(( missing == 0 )) || { printf '\nMissing required commands. No Node Core files have been installed.\n' >&2; exit 1; }
printf '\n=== CANONICAL INSTALLER ===\n'
printf 'The installer will operate in user space and perform its own compatibility checks.\n'
exec bash "$SOURCE_DIR/installer/install.sh" "$@"
