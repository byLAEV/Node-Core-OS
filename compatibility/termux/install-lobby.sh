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
cp "$ROOT/compatibility/termux/lobby/server.py" "$DEST/server.py"
cp "$ROOT/compatibility/termux/lobby/web/"* "$DEST/web/"
chmod 700 "$DEST"
chmod 600 "$DEST/server.py" "$DEST/web/"*
cp "$ROOT/compatibility/termux/lobby/launcher.sh" "$SHORTCUTS/node-core-lobby"
chmod 700 "$SHORTCUTS/node-core-lobby"
if ! command -v python >/dev/null 2>&1; then
  printf 'Python is missing. Install it with: pkg install python\n' >&2
  exit 1
fi
python "$DEST/server.py" --check
printf '\nLobby prototype installed.\n'
printf 'Start it with: bash "$HOME/.shortcuts/node-core-lobby"\n'
printf 'For a home-screen shortcut, install Termux:Widget and add the node-core-lobby script.\n'
