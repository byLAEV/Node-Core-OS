#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
if [[ -z "${PREFIX:-}" || "$PREFIX" != /data/data/com.termux/files/usr ]]; then
  printf 'This installer must run inside native Termux.\n' >&2
  exit 1
fi
if [[ "$(id -u)" == "0" ]]; then
  printf 'Do not run this installer as root.\n' >&2
  exit 1
fi
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
DEST="$HOME/.node-core/lobby"
SHORTCUTS="$HOME/.shortcuts"
mkdir -p "$DEST/web" "$SHORTCUTS"

if ! command -v python >/dev/null 2>&1; then
  printf 'Python is missing. Install it with: pkg install python\n' >&2
  exit 1
fi

# Termux splits the OpenSSL library package from its command-line tools.
# The executable is provided by openssl-tool, not necessarily by openssl.
if ! command -v openssl >/dev/null 2>&1; then
  printf 'OpenSSL command not found; installing Termux openssl-tool...\n'
  if command -v pkg >/dev/null 2>&1; then
    pkg install openssl-tool -y || printf 'WARNING: openssl-tool installation failed; Lobby will use HTTP loopback fallback.\n' >&2
  else
    printf 'WARNING: pkg is unavailable; install openssl-tool manually to enable HTTPS.\n' >&2
  fi
fi
if command -v openssl >/dev/null 2>&1; then
  printf 'OpenSSL executable detected: %s\n' "$(command -v openssl)"
else
  printf 'WARNING: OpenSSL executable still unavailable; HTTPS cannot be enabled yet.\n' >&2
fi

cp "$ROOT/compatibility/termux/lobby/server.py" "$DEST/server.py"
cp "$ROOT/compatibility/termux/lobby/web/"* "$DEST/web/"
cp "$ROOT/compatibility/termux/lobby/launcher.sh" "$SHORTCUTS/node-core-lobby"
chmod 700 "$DEST" "$SHORTCUTS/node-core-lobby"
chmod 600 "$DEST/server.py" "$DEST/web/"*
printf '\nInstalled Lobby files. Restarting server with the updated version...\n'
bash "$SHORTCUTS/node-core-lobby"
