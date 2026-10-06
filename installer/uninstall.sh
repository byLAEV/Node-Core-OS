#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${HOME}/.node-core"
BIN_DIR="${HOME}/.local/bin"

printf '%s\n' "Node Core OS Uninstaller"
printf '%s\n' "byLAEV"
printf '%s\n' ""

rm -f "$BIN_DIR/node-core"
rm -rf "$DATA_DIR/venv" "$DATA_DIR/app"
rm -f "$DATA_DIR/bin/ipfs"
rmdir "$DATA_DIR/bin" 2>/dev/null || true

printf '%s\n' "Node Core runtime and launcher removed."
printf '%s\n' "Node data was preserved at:"
printf '%s\n' "    $DATA_DIR"
printf '%s\n' ""
printf '%s\n' "Kubo installed by Node Core is preserved only if it remains in $DATA_DIR."
