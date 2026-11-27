#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
SOURCE_COMMIT="08d994574775a0ec3d9dcc4b2e88862152d1ea3b"
PACKAGE_NAME="node-core-os"
PACKAGE_VERSION="1.5.6-1"
BUILD_ROOT="$ROOT/build/debian-terminal"
SOURCE_DIR="$BUILD_ROOT/source"
PACKAGE_DIR="$BUILD_ROOT/package"
OUTPUT="$ROOT/build/${PACKAGE_NAME}_${PACKAGE_VERSION}_arm64.deb"

command -v git >/dev/null 2>&1 || { echo "git is required." >&2; exit 1; }
command -v dpkg-deb >/dev/null 2>&1 || { echo "dpkg-deb is required (install dpkg-dev)." >&2; exit 1; }

rm -rf "$BUILD_ROOT"
mkdir -p "$SOURCE_DIR" "$PACKAGE_DIR/DEBIAN" "$PACKAGE_DIR/usr/lib/node-core-os/1.5.6" "$PACKAGE_DIR/usr/bin"

git -C "$ROOT" cat-file -e "${SOURCE_COMMIT}^{commit}"
git -C "$ROOT" archive "$SOURCE_COMMIT" | tar -x -C "$SOURCE_DIR"

test "$(cat "$SOURCE_DIR/VERSION")" = "1.5.6"
test -f "$SOURCE_DIR/main.py"
test -f "$SOURCE_DIR/node_core/ui.py"
test -f "$SOURCE_DIR/node_core/bios.py"

cp -a "$SOURCE_DIR/." "$PACKAGE_DIR/usr/lib/node-core-os/1.5.6/"
install -m 0644 "$ROOT/packaging/debian-terminal/control" "$PACKAGE_DIR/DEBIAN/control"
install -m 0755 "$ROOT/packaging/debian-terminal/node-core-os" "$PACKAGE_DIR/usr/bin/node-core-os"

dpkg-deb --root-owner-group --build "$PACKAGE_DIR" "$OUTPUT"

test "$(dpkg-deb -f "$OUTPUT" Package)" = "$PACKAGE_NAME"
test "$(dpkg-deb -f "$OUTPUT" Version)" = "$PACKAGE_VERSION"
test "$(dpkg-deb -f "$OUTPUT" Architecture)" = "arm64"

echo
echo "Package built and metadata validated:"
dpkg-deb --info "$OUTPUT"
echo
echo "Package contents:"
dpkg-deb --contents "$OUTPUT"
echo
echo "Output: $OUTPUT"
