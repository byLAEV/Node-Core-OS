#!/bin/sh
set -eu
[ "$(id -u)" -ne 0 ] || { echo "Run as normal user." >&2; exit 1; }
rm -rf "$HOME/.local/lib/node-core-os/node_core_os"
rm -f "$HOME/.local/bin/node-core-os"
rmdir "$HOME/.local/lib/node-core-os" 2>/dev/null || true
echo "Program removed; personal data is preserved in ~/.local/share/node-core-os"
