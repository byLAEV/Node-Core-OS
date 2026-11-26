#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$REPOSITORY_ROOT/installer/lib/manifest.sh"

temporary_root="$(mktemp -d)"
trap 'rm -rf "$temporary_root"' EXIT
export HOME="$temporary_root/home"
export NODE_CORE_DATA_DIR="$HOME/.node-core"
mkdir -p "$HOME" "$NODE_CORE_DATA_DIR"

valid_manifest='{"schema_version":1,"application":{"name":"Node Core OS","verified":false},"components":{}}'
node_core_manifest_write "$NODE_CORE_DATA_DIR/installation-manifest.json" "$valid_manifest"
node_core_manifest_validate "$NODE_CORE_DATA_DIR/installation-manifest.json"
python3 - "$NODE_CORE_DATA_DIR/installation-manifest.json" <<'PY'
import json
import os
import stat
import sys
path = sys.argv[1]
with open(path, encoding="utf-8") as stream:
    manifest = json.load(stream)
assert manifest["schema_version"] == 1
assert isinstance(manifest["application"], dict)
assert isinstance(manifest["components"], dict)
assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
PY

if node_core_manifest_write "$NODE_CORE_DATA_DIR/installation-manifest.json" '{"schema_version":2,"application":{},"components":{}}' 2>/dev/null; then
  printf 'FAIL: unsupported schema was written.\n' >&2
  exit 1
fi

printf '{broken json\n' > "$NODE_CORE_DATA_DIR/installation-manifest.json"
if node_core_manifest_validate "$NODE_CORE_DATA_DIR/installation-manifest.json" 2>/dev/null; then
  printf 'FAIL: malformed manifest was accepted.\n' >&2
  exit 1
fi

if node_core_manifest_write "$temporary_root/outside/installation-manifest.json" "$valid_manifest" 2>/dev/null; then
  printf 'FAIL: manifest path outside data directory was accepted.\n' >&2
  exit 1
fi

printf 'Installation manifest tests passed.\n'
