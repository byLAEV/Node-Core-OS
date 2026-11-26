#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
VERSION=$(cat "$ROOT/VERSION")
WORK="$ROOT/.deb-build/node-core-os"
OUT="$ROOT/dist"
rm -rf "$WORK"
mkdir -p "$WORK/usr/lib/node-core-os" "$WORK/DEBIAN" "$OUT"
cp -R "$ROOT/src/node_core_os" "$WORK/usr/lib/node-core-os/"
cp "$ROOT/packaging/debian/control" "$WORK/DEBIAN/control"
sed -i "s/^Version:.*/Version: $VERSION/" "$WORK/DEBIAN/control"
dpkg-deb --build "$WORK" "$OUT/node-core-os_${VERSION}_all.deb"
dpkg-deb --info "$OUT/node-core-os_${VERSION}_all.deb"
(cd "$OUT" && sha256sum "node-core-os_${VERSION}_all.deb" > "node-core-os_${VERSION}_all.deb.sha256")
echo "Package created: $OUT/node-core-os_${VERSION}_all.deb"
