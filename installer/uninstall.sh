#!/usr/bin/env bash
set -euo pipefail

info() { printf '%s\n' "$*"; }

info "Node Core OS Uninstaller"
info "byLAEV"
info

python3 -m pip uninstall -y node-core-os >/dev/null 2>&1 || true
rm -f "$HOME/.local/bin/node-core"

info "Node Core package and launcher removed."
info "User data was preserved at:"
info "    $HOME/.node-core"
info
info "To remove Node Core data too, delete that directory manually."
