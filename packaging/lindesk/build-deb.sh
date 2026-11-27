#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
SOURCE_COMMIT="08d994574775a0ec3d9dcc4b2e88862152d1ea3b"
BUILD="$ROOT/build/node-core-os_1.5.6-1_arm64"
TMP="$ROOT/build/source-1.5.6"
rm -rf "$BUILD" "$TMP"
mkdir -p "$BUILD/DEBIAN" "$BUILD/opt/node-core-os-1.5.6" "$BUILD/usr/bin" "$TMP"
git -C "$ROOT" archive "$SOURCE_COMMIT" | tar -x -C "$TMP"
test "$(cat "$TMP/VERSION")" = "1.5.6"
install -d "$BUILD/opt/node-core-os-1.5.6/source"
cp -a "$TMP/." "$BUILD/opt/node-core-os-1.5.6/source/"
install -m 0755 "$ROOT/packaging/lindesk/install-user.sh" "$BUILD/opt/node-core-os-1.5.6/install-user.sh"
cat > "$BUILD/usr/bin/node-core-os-install-user" <<'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail
exec bash /opt/node-core-os-1.5.6/install-user.sh "$@"
LAUNCHER
chmod 0755 "$BUILD/usr/bin/node-core-os-install-user"
cat > "$BUILD/DEBIAN/control" <<'CONTROL'
Package: node-core-os
Version: 1.5.6-1
Section: utils
Priority: optional
Architecture: arm64
Maintainer: byLAEV
Depends: bash, python3 (>= 3.10)
Description: Node Core OS 1.5.6 user-space installer for LinDesk ARM64
 Historical Node Core OS source and a user-mode installer entry point.
 The package does not run the core installer as root.
CONTROL
cat > "$BUILD/DEBIAN/description" <<'DESCRIPTION'
Node Core OS installs its runtime, Python virtual environment, local data,
and Kubo repository inside the invoking user's HOME directory.
The package maintainer scripts do not execute application installation.
DESCRIPTION
dpkg-deb --root-owner-group --build "$BUILD" "$ROOT/build/node-core-os_1.5.6-1_arm64.deb"
dpkg-deb --info "$ROOT/build/node-core-os_1.5.6-1_arm64.deb"
test "$(dpkg-deb -f "$ROOT/build/node-core-os_1.5.6-1_arm64.deb" Architecture)" = arm64
