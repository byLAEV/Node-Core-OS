#!/bin/sh
# Install Node Core OS for the invoking user only. No sudo, dpkg, or system writes.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
PREFIX=${NODE_CORE_OS_PREFIX:-"$HOME/.local"}
BIN="$PREFIX/bin"
LIB="$PREFIX/lib/node-core-os"
DATA=${NODE_CORE_OS_HOME:-"$HOME/.local/share/node-core-os"}

case "$PREFIX" in
  "$HOME"/*) ;;
  *) echo "Refusing non-user prefix: $PREFIX" >&2; exit 1 ;;
esac
mkdir -p "$BIN" "$LIB" "$DATA"
rm -rf "$LIB/node_core_os"
cp -R "$ROOT/src/node_core_os" "$LIB/"
cat > "$BIN/node-core-os" <<'LAUNCHER'
#!/bin/sh
set -eu
PREFIX=${NODE_CORE_OS_PREFIX:-"$HOME/.local"}
export NODE_CORE_OS_HOME=${NODE_CORE_OS_HOME:-"$HOME/.local/share/node-core-os"}
PYTHONPATH="$PREFIX/lib/node-core-os${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH
exec python3 -m node_core_os "$@"
LAUNCHER
chmod 755 "$BIN/node-core-os"
printf 'Installed for current user only.\nCommand: %s\nData: %s\n' "$BIN/node-core-os" "$DATA"
printf 'Ensure %s is in PATH, then run: node-core-os\n' "$BIN"
