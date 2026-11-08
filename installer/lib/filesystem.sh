#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS installer helpers cannot run as root. Use the normal user account without sudo.\\n' >&2
  return 1 2>/dev/null || exit 1
fi

# The JSON manifest is the canonical source of the relative runtime directory
# layout. Python creates the listed directories without following symlinks.
prepare_filesystem() {
  local manifest="$PROJECT_ROOT/installer/layout-manifest.json"
  [[ -f "$manifest" && ! -L "$manifest" ]] || {
    printf 'Canonical directory layout manifest is missing or unsafe: %s\\n' "$manifest" >&2
    return 1
  }
  python3 - "$manifest" "$NODE_CORE_DATA_DIR" "$HOME" <<'PY'
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath

manifest_path, root_arg, home_arg = map(Path, sys.argv[1:])
data = json.loads(manifest_path.read_text(encoding="utf-8"))
root = Path(os.path.abspath(root_arg))
home = Path(os.path.realpath(home_arg))
if root == home or home not in root.parents:
    raise SystemExit("Unsafe NODE_CORE_DATA_DIR: it must be inside HOME.")
if root.is_symlink() or (root.exists() and not root.is_dir()):
    raise SystemExit(f"Unsafe Node Core OS root: {root}")
if not root.exists():
    root.mkdir(mode=0o700)

for entry in data.get("directories", []):
    relative = PurePosixPath(entry["path"])
    if relative.is_absolute() or not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
        raise SystemExit(f"Unsafe directory path in manifest: {entry['path']!r}")
    current = root
    for part in relative.parts:
        current = current / part
        try:
            current.mkdir(mode=0o700)
        except FileExistsError:
            info = current.lstat()
            if not current.is_dir() or current.is_symlink():
                raise SystemExit(f"Refusing unsafe directory component: {current}")
        if current.is_symlink():
            raise SystemExit(f"Refusing symbolic link in runtime layout: {current}")
        if root not in current.parents:
            raise SystemExit(f"Directory escaped Node Core OS root: {current}")

print(f"Created/verified {len(data['directories'])} canonical directories under {root}")
PY
}
