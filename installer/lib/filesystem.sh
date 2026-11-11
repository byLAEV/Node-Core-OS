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
import stat
import sys
from pathlib import Path, PurePosixPath

manifest_path, root_arg, home_arg = map(Path, sys.argv[1:])
data = json.loads(manifest_path.read_text(encoding="utf-8"))
home = Path(os.path.realpath(home_arg))
root = Path(os.path.abspath(root_arg))
try:
    root_relative = root.relative_to(home)
except ValueError:
    raise SystemExit("Unsafe NODE_CORE_DATA_DIR: it must be inside HOME.")
if not root_relative.parts:
    raise SystemExit("Unsafe NODE_CORE_DATA_DIR: it cannot equal HOME.")

# Check every existing component below HOME, not just the final root. A
# symlink in ~/.node-core could otherwise redirect all later mkdir calls.
current = home
for part in root_relative.parts:
    current = current / part
    try:
        current.mkdir(mode=0o700)
    except FileExistsError:
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise SystemExit(f"Refusing unsafe data-root component: {current}")

for entry in data.get("directories", []):
    if entry.get("provisioner") != "node-core-installer":
        continue
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
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise SystemExit(f"Refusing unsafe directory component: {current}")
        if current.is_symlink():
            raise SystemExit(f"Refusing symbolic link in runtime layout: {current}")
        if root not in current.parents:
            raise SystemExit(f"Directory escaped Node Core OS root: {current}")

print(f"Created/verified {len(data['directories'])} canonical directories under {root}")
PY
}
