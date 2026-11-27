#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
PKG="$ROOT/build/node-core-os-gui_1.5.6-2_all"
rm -rf "$PKG"
install -d "$PKG/DEBIAN" "$PKG/usr/lib/node-core-os-gui" "$PKG/usr/bin" "$PKG/usr/share/applications"
install -m 0644 "$ROOT/packaging/gui-arm64/control" "$PKG/DEBIAN/control"
install -m 0755 "$ROOT/packaging/gui-arm64/app.py" "$PKG/usr/lib/node-core-os-gui/app.py"
printf '%s\n' '#!/bin/sh' 'exec /usr/bin/python3 /usr/lib/node-core-os-gui/app.py "$@"' > "$PKG/usr/bin/node-core-os-gui"
chmod 0755 "$PKG/usr/bin/node-core-os-gui"
install -m 0644 "$ROOT/packaging/gui-arm64/node-core-os-gui.desktop" "$PKG/usr/share/applications/node-core-os-gui.desktop"
dpkg-deb --root-owner-group --build "$PKG" "$ROOT/build/node-core-os-gui_1.5.6-2_all.deb"
dpkg-deb --info "$ROOT/build/node-core-os-gui_1.5.6-2_all.deb"
