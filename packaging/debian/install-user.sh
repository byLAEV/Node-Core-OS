#!/bin/sh
# Install for the current user only; never invokes sudo or su.
set -eu
[ "$(id -u)" -ne 0 ] || { echo "Do not run as root." >&2; exit 1; }
PACKAGE=${1:-}
[ -n "$PACKAGE" ] && [ -f "$PACKAGE" ] || { echo "Usage: sh install-user.sh ./node-core-os_VERSION_all.deb" >&2; exit 2; }
command -v dpkg-deb >/dev/null 2>&1 || { echo "dpkg-deb is required; extraction needs no root." >&2; exit 1; }
BASE="$HOME/.local"
APP="$BASE/lib/node-core-os"
BIN="$BASE/bin"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
dpkg-deb -x "$PACKAGE" "$TMP"
mkdir -p "$APP" "$BIN"
rm -rf "$APP/node_core_os"
cp -R "$TMP/usr/lib/node-core-os/node_core_os" "$APP/"
cat > "$BIN/node-core-os" <<'LAUNCHER'
#!/bin/sh
set -eu
PYTHONPATH="$HOME/.local/lib/node-core-os${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH
exec python3 -m node_core_os "$@"
LAUNCHER
chmod 0755 "$BIN/node-core-os"
echo "Installed locally: $BIN/node-core-os"
echo "No root, sudo, system service, or system path was used."
echo "Add $BIN to PATH if needed."
