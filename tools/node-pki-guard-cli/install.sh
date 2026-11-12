#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required (3.10 or newer)." >&2
  exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || {
  echo "ERROR: Python 3.10 or newer is required; found $PYTHON_VERSION." >&2
  exit 1
}
if ! command -v openssl >/dev/null 2>&1; then
  echo "ERROR: OpenSSL is required and must be available on PATH." >&2
  exit 1
fi
OPENSSL_VERSION=$(openssl version)
echo "Using $OPENSSL_VERSION"

if command -v pipx >/dev/null 2>&1; then
  pipx install --force "$SCRIPT_DIR"
else
  python3 -m pip install --user --upgrade "$SCRIPT_DIR"
  echo "If node-pki-guard is not found, add ~/.local/bin to PATH."
fi

echo "Installed. Run: node-pki-guard --help"
