#!/usr/bin/env bash
# Node Core OS — one-command installer/updater bootstrap.
# Downloads the official repository snapshot, then delegates all installation
# and migration work to the repository's tested installer entry point.
set -Eeuo pipefail

REPOSITORY="https://github.com/byLAEV/Node-Core-OS"
BRANCH="${NODE_CORE_BRANCH:-main}"

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS must run as your normal user. Do not use sudo or root.\n' >&2
  exit 1
fi

if [[ ! "$BRANCH" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  printf 'Invalid NODE_CORE_BRANCH value.\n' >&2
  exit 1
fi

if ! command -v tar >/dev/null 2>&1; then
  printf 'Missing required command: tar\n' >&2
  if [[ -n "${TERMUX_VERSION:-}" ]] && command -v pkg >/dev/null 2>&1; then
    printf 'Installing tar with Termux pkg...\n'
    pkg install -y tar
  else
    printf 'Install tar with your Linux distribution package manager, then retry.\n' >&2
    exit 1
  fi
fi

if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
  if [[ -n "${TERMUX_VERSION:-}" ]] && command -v pkg >/dev/null 2>&1; then
    printf 'Installing curl with Termux pkg...\n'
    pkg install -y curl
  else
    printf 'Missing download tool: install curl or wget, then retry.\n' >&2
    exit 1
  fi
fi

TMP_ROOT="${TMPDIR:-${PREFIX:-/tmp}}"
WORK_DIR="$(mktemp -d "$TMP_ROOT/node-core-bootstrap.XXXXXX")"
cleanup() {
  rm -rf -- "$WORK_DIR"
}
trap cleanup EXIT INT TERM

ARCHIVE="$WORK_DIR/node-core.tar.gz"
EXTRACT_DIR="$WORK_DIR/source"
mkdir -p "$EXTRACT_DIR"

ARCHIVE_URL="https://codeload.github.com/byLAEV/Node-Core-OS/tar.gz/refs/heads/$BRANCH"
printf '%s\n' 'Node Core OS — actualización e instalación'
printf 'Repositorio: %s\n' "$REPOSITORY"
printf 'Rama: %s\n' "$BRANCH"
printf '\nDescargando el código oficial...\n'

if command -v curl >/dev/null 2>&1; then
  curl --fail --location --silent --show-error \
    --connect-timeout 20 --retry 3 --retry-delay 2 \
    --output "$ARCHIVE" "$ARCHIVE_URL"
else
  wget --quiet --timeout=20 --tries=4 \
    --output-document="$ARCHIVE" "$ARCHIVE_URL"
fi

tar -tzf "$ARCHIVE" >/dev/null 2>&1 || {
  printf 'El archivo descargado no es un paquete TAR.GZ válido.\n' >&2
  exit 1
}

tar -xzf "$ARCHIVE" -C "$EXTRACT_DIR" \
  --no-same-owner --no-same-permissions

SOURCE_DIR="$(find "$EXTRACT_DIR" -mindepth 1 -maxdepth 1 -type d -print -quit)"
if [[ -z "$SOURCE_DIR" || ! -f "$SOURCE_DIR/VERSION" || \
      ! -f "$SOURCE_DIR/installer/install.sh" || \
      ! -f "$SOURCE_DIR/installer/update.sh" ]]; then
  printf 'El repositorio descargado no contiene los archivos de instalación esperados.\n' >&2
  exit 1
fi

VERSION="$(tr -d '\r\n' < "$SOURCE_DIR/VERSION")"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  printf 'La versión del repositorio descargado no es válida: %s\n' "$VERSION" >&2
  exit 1
fi

printf '\nVersión del repositorio: %s\n' "$VERSION"
printf '%s\n' 'Iniciando el instalador oficial...'
printf '%s\n' 'Si ya existe una instalación, el instalador delegará en el actualizador protegido.'
printf '%s\n' 'Los datos persistentes de Node Core e IPFS deben conservarse.'
printf '\n'

export NODE_CORE_BRANCH="$BRANCH"
bash "$SOURCE_DIR/installer/install.sh" "$@"
