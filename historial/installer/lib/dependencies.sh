#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS installer helpers cannot run as root. Use the normal user account without sudo.\n' >&2
  return 1 2>/dev/null || exit 1
fi

python_version_ok() {
  python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
}

check_dependencies() {
  local missing=0 command_name
  for command_name in bash python3 tar sha512sum mkdir cp rm mktemp uname awk realpath stat id find grep sed nohup; do
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

linux_terminal_install_missing_dependencies() {
  local -a packages=()
  local command_name
  node_core_is_termux || return 0

  command -v bash >/dev/null 2>&1 || packages+=(bash)
  command -v python3 >/dev/null 2>&1 || packages+=(python)
  command -v tar >/dev/null 2>&1 || packages+=(tar)
  command -v curl >/dev/null 2>&1 || packages+=(curl)
  command -v grep >/dev/null 2>&1 || packages+=(grep)
  command -v sed >/dev/null 2>&1 || packages+=(sed)
  command -v find >/dev/null 2>&1 || packages+=(findutils)
  command -v awk >/dev/null 2>&1 || packages+=(gawk)
  for command_name in sha512sum realpath stat mkdir cp rm mktemp uname id; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
      packages+=(coreutils)
      break
    fi
  done
  if ! python3 -c 'import cryptography, re; version=tuple(map(int,re.match(r"^(\d+)\.(\d+)\.(\d+)",cryptography.__version__).groups())); raise SystemExit(version < (42,0,0))' >/dev/null 2>&1; then
    packages+=(python-cryptography)
  fi
  [[ -x "$PREFIX/bin/ipfs" ]] || packages+=(kubo)

  if (("${#packages[@]}" == 0)); then
    printf 'Linux terminal dependencies are already available.\n'
    return 0
  fi
  printf 'Preparing missing Linux terminal packages: %s\n' "${packages[*]}"
  pkg install -y "${packages[@]}"
}

ensure_dependencies() {
  linux_terminal_install_missing_dependencies
  if ! check_dependencies; then
    printf 'Missing installer dependencies. Install them in your Linux terminal and run the installer again.\n' >&2
    printf 'Node Core OS does not require root or sudo.\n' >&2
    return 1
  fi
  check_python
  if node_core_is_termux; then
    python3 -c 'import cryptography, re; from cryptography.hazmat.primitives.asymmetric import ed25519; version=tuple(map(int,re.match(r"^(\d+)\.(\d+)\.(\d+)",cryptography.__version__).groups())); assert version >= (42,0,0); ed25519.Ed25519PrivateKey.generate()' || {
      printf 'Termux Python cryptography is unavailable. Install python-cryptography using pkg.\n' >&2
      return 1
    }
    [[ -x "$PREFIX/bin/ipfs" ]] || {
      printf 'Termux Kubo is unavailable. Install the kubo package using pkg.\n' >&2
      return 1
    }
  fi
}

check_python() {
  if ! python_version_ok; then
    printf 'Python 3.10 or newer is required.\n' >&2
    return 1
  fi
}
