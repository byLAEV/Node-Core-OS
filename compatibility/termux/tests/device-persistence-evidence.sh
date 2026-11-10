#!/usr/bin/env bash
# Physical Termux acceptance evidence for the five persistent Node Core OS scopes.
# Private SHA-256 manifests remain on this device and are never printed or uploaded.
set -Eeuo pipefail
umask 077

usage() {
  cat <<'EOF'
Termux physical persistence acceptance

Run from the Node Core OS candidate checkout as the ordinary Termux user:

  bash compatibility/termux/tests/device-persistence-evidence.sh capture-before
  # Execute the official updater from the Lobby and wait for success.
  bash compatibility/termux/tests/device-persistence-evidence.sh compare-update
  # Stop and restart the Lobby service using its normal launcher.
  bash compatibility/termux/tests/device-persistence-evidence.sh compare-restart

Private SHA-256 manifests are stored only in:
  ~/.node-core/runtime/termux-device-acceptance/

Share only the command output and summary-*.json files. Never share before.json,
after-update.json or after-lobby-restart.json: they contain hashes of identity files.
EOF
}

ACTION="\${1:-}"
case "$ACTION" in
  capture-before|compare-update|compare-restart) ;;
  -h|--help|"") usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

[[ "$(uname -s)" == "Linux" ]] || fail "This acceptance script requires native Termux on Android."
[[ "$(id -u)" -ne 0 ]] || fail "Run as the normal Termux user, never root."
[[ -n "\${TERMUX_VERSION:-}" ]] || fail "TERMUX_VERSION is missing; this is not a native Termux session."
[[ "\${PREFIX:-}" == "/data/data/com.termux/files/usr" ]] || fail "PREFIX is not the native Termux prefix."
[[ "$(uname -m)" == "aarch64" ]] || fail "Native Termux acceptance requires uname -m=aarch64."
[[ -n "\${HOME:-}" && -d "$HOME" ]] || fail "HOME is missing or unavailable."
command -v curl >/dev/null 2>&1 || fail "curl is required for the post-restart Lobby health check."

NODE_CORE_DATA_DIR="\${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
APP_DIR="$NODE_CORE_DATA_DIR/app"
RUNTIME_DIR="$NODE_CORE_DATA_DIR/runtime"
EVIDENCE_DIR="$RUNTIME_DIR/termux-device-acceptance"

[[ ! -L "$NODE_CORE_DATA_DIR" ]] || fail "Node Core data directory must not be a symlink."
[[ -d "$NODE_CORE_DATA_DIR" ]] || fail "Node Core is not installed under $NODE_CORE_DATA_DIR."
[[ ! -L "$RUNTIME_DIR" ]] || fail "Runtime directory must not be a symlink."
[[ -d "$APP_DIR" && ! -L "$APP_DIR" ]] || fail "Installed Node Core application directory is missing or unsafe."

PYTHON_BIN="$RUNTIME_DIR/node-core-venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi
[[ -n "$PYTHON_BIN" && -x "$PYTHON_BIN" ]] || fail "Python 3 is required."
export NODE_CORE_DATA_DIR
export PYTHONPATH="$APP_DIR\${PYTHONPATH:+:$PYTHONPATH}"

mkdir -p "$EVIDENCE_DIR"
chmod 700 "$EVIDENCE_DIR"
[[ ! -L "$EVIDENCE_DIR" ]] || fail "Evidence directory must not be a symlink."

if [[ "$ACTION" == "compare-restart" ]]; then
  health=''
  if health="$(curl --insecure --fail --silent --show-error --max-time 5 \
      "https://127.0.0.1:8765/health" 2>/dev/null)"; then
    :
  elif health="$(curl --fail --silent --show-error --max-time 5 \
      "http://127.0.0.1:8765/health" 2>/dev/null)"; then
    :
  else
    fail "Lobby health endpoint did not respond after the restart. Start the Lobby, then retry."
  fi
  NODE_CORE_HEALTH_JSON="$health" "$PYTHON_BIN" - <<'PY'
import json
import os
try:
    health = json.loads(os.environ["NODE_CORE_HEALTH_JSON"])
except (KeyError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Lobby health response is not valid JSON: {exc}")
if not isinstance(health, dict):
    raise SystemExit("Lobby health endpoint did not return a JSON object.")
print("Lobby local health endpoint returned HTTP 200 and valid JSON after restart: PASS.")
PY
fi

"$PYTHON_BIN" - "$ACTION" "$NODE_CORE_DATA_DIR" "$EVIDENCE_DIR" <<'PY'
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from node_core.persistence_integrity import (
    PersistenceIntegrityError,
    capture_persistence_manifest,
    compare_persistence_manifests,
    read_persistence_manifest,
    write_persistence_manifest,
)

action, data_arg, evidence_arg = sys.argv[1:4]
data_root = Path(data_arg)
evidence_dir = Path(evidence_arg)
uid = os.getuid()
home = Path.home().resolve()
data_lstat = data_root.lstat()
if stat.S_ISLNK(data_lstat.st_mode) or not stat.S_ISDIR(data_lstat.st_mode):
    raise SystemExit("Node Core data directory is not a real directory.")
if data_lstat.st_uid != uid:
    raise SystemExit("Node Core data directory is not owned by the current Termux user.")
resolved_data = data_root.resolve(strict=True)
if resolved_data == home or home not in resolved_data.parents:
    raise SystemExit("Node Core data directory must remain inside the current user's HOME.")
for path in (data_root / "runtime", evidence_dir):
    if path.is_symlink():
        raise SystemExit(f"Refusing symlinked acceptance path: {path.name}")
    if not path.is_dir():
        raise SystemExit(f"Acceptance path is unavailable: {path.name}")
if evidence_dir.stat().st_uid != uid:
    raise SystemExit("Acceptance evidence directory is not owned by the current user.")
if stat.S_IMODE(evidence_dir.stat().st_mode) != 0o700:
    raise SystemExit("Acceptance evidence directory permissions must be 0700.")

app_dir = data_root / "app"
required = (
    data_root / "identity" / "node.json",
    data_root / "identity" / "private" / "node.key",
    data_root / "identity" / "profile.json",
    data_root / "identity" / "entity-registry.json",
    data_root / "storage",
    data_root / "ipfs",
)
for path in required:
    if not path.exists() or path.is_symlink():
        raise SystemExit(f"Required persistent path is missing or unsafe: {path.relative_to(data_root)}")

phase_files = {
    "capture-before": ("before.json", "summary-before.json"),
    "compare-update": ("after-update.json", "summary-after-update.json"),
    "compare-restart": ("after-lobby-restart.json", "summary-after-lobby-restart.json"),
}
manifest_name, summary_name = phase_files[action]
manifest_path = evidence_dir / manifest_name
summary_path = evidence_dir / summary_name
if manifest_path.exists() or summary_path.exists():
    raise SystemExit(f"Evidence already exists for {action}; preserve it and use a fresh acceptance directory.")

def capture() -> dict:
    manifest = capture_persistence_manifest(
        data_root,
        storage_dir=data_root / "storage",
        kubo_repo=data_root / "ipfs",
    )
    expected = {
        "node_identity",
        "profile",
        "entity_registry",
        "local_storage",
        "kubo_ipfs",
    }
    if set(manifest["scopes"]) != expected:
        raise PersistenceIntegrityError("The manifest does not contain exactly the five required scopes.")
    return manifest

def write_private_json(path: Path, payload: dict) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".summary-", dir=str(path.parent))
    temporary_path = Path(temporary)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise

def safe_metadata() -> dict:
    version_path = app_dir / "VERSION"
    commit_path = data_root / "runtime" / "node-core-commit"
    version = version_path.read_text(encoding="utf-8").strip() if version_path.is_file() else "unknown"
    commit = commit_path.read_text(encoding="utf-8").strip() if commit_path.is_file() else "unknown"
    return {
        "device_architecture": os.uname().machine,
        "termux_version": os.environ.get("TERMUX_VERSION", "unknown"),
        "prefix": os.environ.get("PREFIX", "unknown"),
        "uid": uid,
        "node_core_version": version,
        "node_core_commit": commit,
    }

def scope_summary(manifest: dict) -> dict:
    return {
        name: {
            "file_count": item["file_count"],
            "total_bytes": item["total_bytes"],
        }
        for name, item in sorted(manifest["scopes"].items())
    }

def compare_or_fail(before: dict, after: dict, label: str) -> None:
    result = compare_persistence_manifests(before, after)
    if not result["matches"]:
        print(f"FAIL: persistence mismatch {label}.", file=sys.stderr)
        for key in ("added", "removed", "changed", "added_scopes", "removed_scopes"):
            if result[key]:
                print(f"{key}: " + ", ".join(result[key]), file=sys.stderr)
        if result["policy_changed"]:
            print("policy_changed: true", file=sys.stderr)
        raise SystemExit(1)

try:
    if action == "capture-before":
        manifest = capture()
        write_persistence_manifest(manifest_path, manifest)
        summary = {
            "schema_version": 1,
            "phase": "before_update",
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "host": safe_metadata(),
            "scopes": scope_summary(manifest),
            "private_manifest": manifest_name,
            "private_manifest_mode": "0600",
        }
        write_private_json(summary_path, summary)
        print("PASS: baseline captured for NODE ID, profile, entity registry, local storage and Kubo/IPFS.")
        print("Private baseline manifest saved locally with permissions 0600.")
    elif action == "compare-update":
        before_path = evidence_dir / "before.json"
        if not before_path.is_file() or before_path.is_symlink():
            raise SystemExit("Run capture-before after the clean installation and identity association first.")
        before = read_persistence_manifest(before_path)
        after = capture()
        compare_or_fail(before, after, "after official update")
        write_persistence_manifest(manifest_path, after)
        summary = {
            "schema_version": 1,
            "phase": "after_official_update",
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "host": safe_metadata(),
            "scopes": scope_summary(after),
            "comparison": "match_all_five_scopes",
            "private_manifest": manifest_name,
            "private_manifest_mode": "0600",
        }
        write_private_json(summary_path, summary)
        print("PASS: all five SHA-256 persistence scopes match before and after the official update.")
    elif action == "compare-restart":
        before_path = evidence_dir / "before.json"
        update_path = evidence_dir / "after-update.json"
        for path in (before_path, update_path):
            if not path.is_file() or path.is_symlink():
                raise SystemExit("Run capture-before and compare-update before checking Lobby restart recovery.")
        before = read_persistence_manifest(before_path)
        after_update = read_persistence_manifest(update_path)
        after_restart = capture()
        compare_or_fail(before, after_restart, "after Lobby restart")
        compare_or_fail(after_update, after_restart, "between update and Lobby restart")
        write_persistence_manifest(manifest_path, after_restart)
        summary = {
            "schema_version": 1,
            "phase": "after_lobby_restart",
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "host": safe_metadata(),
            "scopes": scope_summary(after_restart),
            "comparison": "match_all_five_scopes_before_update_after_update_and_after_restart",
            "lobby_health": "ok",
            "private_manifest": manifest_name,
            "private_manifest_mode": "0600",
        }
        write_private_json(summary_path, summary)
        print("PASS: all five SHA-256 scopes match before update, after update and after Lobby restart.")
        print("PASS: NODE ID, profile and entity registry remain recoverable.")
    else:
        raise SystemExit("Unknown acceptance action.")
except (OSError, ValueError, PersistenceIntegrityError) as exc:
    raise SystemExit(f"Persistence acceptance failed safely: {exc}") from exc
PY
