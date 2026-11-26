#!/usr/bin/env bash
set -euo pipefail

# Manifest operations are explicit and scoped to NODE_CORE_DATA_DIR.
# They never run as root, create no host-level files, and do not infer that
# components work merely because the manifest says they are installed.

node_core_manifest_validate() {
  local manifest_path="${1:-${NODE_CORE_DATA_DIR:-$HOME/.node-core}/installation-manifest.json}"
  [[ -f "$manifest_path" && ! -L "$manifest_path" ]] || {
    printf 'Installation manifest is missing or is a symbolic link: %s\n' "$manifest_path" >&2
    return 1
  }

  python3 - "$manifest_path" <<'PY'
import json
import sys

path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as stream:
        value = json.load(stream)
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    print(f"Invalid installation manifest: {exc}", file=sys.stderr)
    raise SystemExit(1)

if not isinstance(value, dict):
    print("Invalid installation manifest: root must be an object", file=sys.stderr)
    raise SystemExit(1)
if value.get("schema_version") != 1:
    print("Invalid installation manifest: unsupported schema_version", file=sys.stderr)
    raise SystemExit(1)
if not isinstance(value.get("application"), dict):
    print("Invalid installation manifest: application must be an object", file=sys.stderr)
    raise SystemExit(1)
if not isinstance(value.get("components"), dict):
    print("Invalid installation manifest: components must be an object", file=sys.stderr)
    raise SystemExit(1)
PY
}

node_core_manifest_write() {
  local manifest_path="${1:-${NODE_CORE_DATA_DIR:-$HOME/.node-core}/installation-manifest.json}"
  local manifest_json="${2:-}"
  local data_dir="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"

  [[ -n "$manifest_json" ]] || {
    printf 'Manifest JSON content is required.\n' >&2
    return 1
  }
  [[ -d "$data_dir" && ! -L "$data_dir" ]] || {
    printf 'Node Core OS data directory must already exist and must not be a symbolic link.\n' >&2
    return 1
  }
  [[ "$(id -u)" != "0" ]] || {
    printf 'Refusing to write the installation manifest as root.\n' >&2
    return 1
  }
  [[ "$(stat -c '%u' "$data_dir")" == "$(id -u)" ]] || {
    printf 'Refusing to write the installation manifest: data directory is not owned by this user.\n' >&2
    return 1
  }

  python3 - "$data_dir" "$manifest_path" "$manifest_json" <<'PY' || return 1
import json
import os
import pathlib
import stat
import sys
import tempfile

data_dir = pathlib.Path(sys.argv[1]).resolve(strict=True)
target_arg = pathlib.Path(sys.argv[2])
raw = sys.argv[3]

try:
    value = json.loads(raw)
except json.JSONDecodeError as exc:
    print(f"Refusing invalid manifest JSON: {exc}", file=sys.stderr)
    raise SystemExit(1)

if not isinstance(value, dict) or value.get("schema_version") != 1:
    print("Refusing manifest: root must be an object with schema_version 1", file=sys.stderr)
    raise SystemExit(1)
if not isinstance(value.get("application"), dict) or not isinstance(value.get("components"), dict):
    print("Refusing manifest: application and components must be objects", file=sys.stderr)
    raise SystemExit(1)

target = target_arg if target_arg.is_absolute() else data_dir / target_arg
parent = target.parent.resolve(strict=True)
if parent != data_dir:
    print("Refusing manifest path outside the Node Core OS data directory", file=sys.stderr)
    raise SystemExit(1)
if target.name != "installation-manifest.json":
    print("Refusing unexpected manifest filename", file=sys.stderr)
    raise SystemExit(1)
if target.is_symlink():
    print("Refusing to replace a symbolic-link manifest", file=sys.stderr)
    raise SystemExit(1)
if target.exists() and not stat.S_ISREG(target.stat().st_mode):
    print("Refusing to replace a non-regular manifest", file=sys.stderr)
    raise SystemExit(1)

serialized = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
fd, temporary = tempfile.mkstemp(prefix=".installation-manifest.", suffix=".tmp", dir=str(data_dir))
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(serialized)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)
    dir_fd = os.open(data_dir, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
except BaseException:
    try:
        os.unlink(temporary)
    except FileNotFoundError:
        pass
    raise
PY
  node_core_manifest_validate "$manifest_path"
}
