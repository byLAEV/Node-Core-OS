#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
VERSION=$(cat "$ROOT/VERSION")
ARCH=$(dpkg --print-architecture 2>/dev/null || true)

if [ "$ARCH" != "arm64" ]; then
    echo "Error: build this package on native Debian ARM64 (detected: ${ARCH:-unknown})." >&2
    echo "Cross-build support is intentionally not claimed by this script." >&2
    exit 1
fi

command -v dpkg-deb >/dev/null 2>&1 || {
    echo "Error: dpkg-deb is required." >&2
    exit 1
}

WORK="$ROOT/.deb-build/node-core-os"
OUT="$ROOT/dist"
rm -rf "$WORK"
mkdir -p "$WORK/usr/lib/node-core-os" "$WORK/usr/bin" "$WORK/DEBIAN" "$OUT"

cp -R "$ROOT/src/node_core_os" "$WORK/usr/lib/node-core-os/"
cat > "$WORK/usr/bin/node-core-os" <<'LAUNCHER'
#!/bin/sh
set -eu
PYTHONPATH=/usr/lib/node-core-os${PYTHONPATH:+:$PYTHONPATH}
export PYTHONPATH
exec python3 -m node_core_os "$@"
LAUNCHER
chmod 0755 "$WORK/usr/bin/node-core-os"
cp "$ROOT/packaging/debian/control" "$WORK/DEBIAN/control"
sed -i "s/^Version:.*/Version: $VERSION/" "$WORK/DEBIAN/control"

dpkg-deb --root-owner-group --build "$WORK" "$OUT/node-core-os_${VERSION}_arm64.deb"
dpkg-deb --info "$OUT/node-core-os_${VERSION}_arm64.deb"
sha256sum "$OUT/node-core-os_${VERSION}_arm64.deb" > "$OUT/node-core-os_${VERSION}_arm64.deb.sha256"
echo "Package created: $OUT/node-core-os_${VERSION}_arm64.deb"
