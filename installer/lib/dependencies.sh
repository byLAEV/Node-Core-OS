#!/usr/bin/env bash
set -euo pipefail
python_version_ok() {
  python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
}
check_dependencies() {
  local missing=0 command_name
  for command_name in bash python3 tar sha512sum mkdir cp rm mktemp uname awk; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
      printf 'Missing required command: %s\n' "$command_name" >&2
      missing=1
    fi
  done
  if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    printf 'Missing required download command: curl or wget\n' >&2
    missing=1
  fi
  return "$missing"
}
detect_package_manager() {
  if command -v apt-get >/dev/null 2>&1; then echo apt
  elif command -v dnf >/dev/null 2>&1; then echo dnf
  elif command -v yum >/dev/null 2>&1; then echo yum
  elif command -v pacman >/dev/null 2>&1; then echo pacman
  elif command -v zypper >/dev/null 2>&1; then echo zypper
  else return 1
  fi
}
install_missing_dependencies() {
  local pm
  pm="$(detect_package_manager)" || { printf 'No supported Linux package manager found. Install missing dependencies manually.\n' >&2; return 1; }
  local packages=(python3 tar coreutils gawk)
  if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then packages+=(curl); fi
  if [[ "$EUID" -eq 0 ]]; then
    case "$pm" in
      apt) apt-get update && apt-get install -y "${packages[@]}" ;;
      dnf) dnf install -y "${packages[@]}" ;;
      yum) yum install -y "${packages[@]}" ;;
      pacman) pacman -Sy --needed --noconfirm "${packages[@]}" ;;
      zypper) zypper --non-interactive install "${packages[@]}" ;;
    esac
  elif command -v sudo >/dev/null 2>&1; then
    case "$pm" in
      apt) sudo apt-get update && sudo apt-get install -y "${packages[@]}" ;;
      dnf) sudo dnf install -y "${packages[@]}" ;;
      yum) sudo yum install -y "${packages[@]}" ;;
      pacman) sudo pacman -Sy --needed --noconfirm "${packages[@]}" ;;
      zypper) sudo zypper --non-interactive install "${packages[@]}" ;;
    esac
  else
    printf 'Missing dependencies and sudo is unavailable. Required packages: %s\n' "${packages[*]}" >&2
    return 1
  fi
}
ensure_dependencies() {
  if ! check_dependencies; then
    install_missing_dependencies
    check_dependencies
  fi
  check_python
}
check_python() {
  if ! python_version_ok; then
    printf 'Python 3.10 or newer is required.\n' >&2
    return 1
  fi
}
