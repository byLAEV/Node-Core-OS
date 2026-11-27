#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
PKG="$ROOT/build/node-core-os-gui_1.5.6-1_arm64"
rm -rf "$PKG"
install -d "$PKG/DEBIAN" "$PKG/usr/share/node-core-os-gui" "$PKG/usr/bin" "$PKG/usr/share/applications"
install -m 0644 "$ROOT/packaging/gui-arm64/control" "$PKG/DEBIAN/control"
install -m 0755 "$ROOT/packaging/gui-arm64/app.py" "$PKG/usr/share/node-core-os-gui/app.py"
cat > "$PKG/usr/bin/node-core-os-gui" <<'LAUNCHER'
#!/bin/sh
exec /usr/bin/python3 /usr/share/node-core-os-gui/app.py "$@"
LAUNCHER
chmod 0755 "$PKG/usr/bin/node-core-os-gui"
install -m 0644 "$ROOT/packaging/gui-arm64/node-core-os-gui.desktop" "$PKG/usr/share/applications/node-core-os-gui.desktop"
dpkg-deb --root-owner-group --build "$PKG" "$ROOT/build/node-core-os-gui_1.5.6-1_arm64.deb"
dpkg-deb --info "$ROOT/build/node-core-os-gui_1.5.6-1_arm64.deb"
