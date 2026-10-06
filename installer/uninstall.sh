#!/usr/bin/env bash
set -euo pipefail

info() { printf '%s\n' "$*"; }

info "Node Core OS Uninstaller"
info "byLAEV"
info

rm -f "$HOME/.local/bin/node-core"
rm -rf "$HOME/.node-core/venv"

info "Node Core runtime and launcher removed."
info "Node data was preserved at:"
info "    $HOME/.node-core"
info
info "To remove Node Core data too, delete that directory manually."
