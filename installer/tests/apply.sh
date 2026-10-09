#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$REPOSITORY_ROOT/installer/lib/apply.sh"

temporary_root="$(mktemp -d)"
trap 'rm -rf "$temporary_root"' EXIT
export HOME="$temporary_root/home"
export NODE_CORE_DATA_DIR="$HOME/.node-core"
mkdir -p "$HOME" "$NODE_CORE_DATA_DIR/app/node_core" "$NODE_CORE_DATA_DIR/storage" "$NODE_CORE_DATA_DIR/ipfs" "$NODE_CORE_DATA_DIR/runtime"

# Seed existing application and persistent user data.
printf 'print("old app")\n' > "$NODE_CORE_DATA_DIR/app/main.py"
printf 'VALUE = "old"\n' > "$NODE_CORE_DATA_DIR/app/node_core/__init__.py"
printf 'preserve local data\n' > "$NODE_CORE_DATA_DIR/storage/user-data.txt"
printf 'preserve ipfs repo\n' > "$NODE_CORE_DATA_DIR/ipfs/config"
printf '{"custom":"keep"}\n' > "$NODE_CORE_DATA_DIR/config.json"
printf 'old-commit\n' > "$NODE_CORE_DATA_DIR/runtime/node-core-commit"

# Fixed or stale staging paths must not be removed by a later transaction.
mkdir -p "$NODE_CORE_DATA_DIR/runtime/update/app-stage"
printf 'recoverable sentinel\n' > "$NODE_CORE_DATA_DIR/runtime/update/app-stage/sentinel.txt"

source_dir="$temporary_root/release"
mkdir -p "$source_dir/node_core"
printf 'print("new app")\n' > "$source_dir?main.py"
printf 'VALUE = "new"\n' > "$source_dir/node_core/__init__.py"

node_core_apply_application "$source_dir" "new-commit-123"

grep -q 'new app' "$NODE_CORE_DATA_DIR/app/main.py"
grep -qx 'new-commit-123' "$NODE_CORE_DATA_DIR/runtime/node-core-commit"
grep -qx 'preserve local data' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
grep -qx 'preserve ipfs repo' "$NODE_CORE_DATA_DIR/ipfs/config"
grep -qx '{"custom":"keep"}' "$NODE_CORE_DATA_DIR/config.json"
grep -qx 'recoverable sentinel' "$NODE_CORE_DATA_DIR/runtime/update/app-stage/sentinel.txt"
backup_count="$(find "$NODE_CORE_DATA_DIR/runtime/backups" -mindepth 1 -maxdepth 1 -type d -name 'app-*' | wc -l)"
[[ "$backup_count" == "1" ]]

# A broken release must fail before touching the current application.
bad_source="$temporary_root/bad-release"
mkdir -p "$bad_source/node_core"
printf 'def broken(:\n' > "$bad_source/main.py"
printf 'VALUE = "bad"\n' > "$bad_source/node_core/__init__.py"
if node_core_apply_application "$bad_source" "bad-commit" 2>/dev/null; then
  printf 'FAIL: invalid Python release was accepted.\n' >&2
  exit 1
fi
grep -q 'new app' "$NODE_CORE_DATA_DIR/app/main.py"
grep -qx 'new-commit-123' "$NODE_CORE_DATA_DIR/runtime/node-core-commit"

# A symbolic-link update directory must be rejected without changing live files.
update_dir="$NODE_CORE_DATA_DIR/runtime/update"
saved_update_dir="$temporary_root/update-directory-saved"
outside_update_dir="$temporary_root/outside-update"
mv "$update_dir" "$saved_update_dir"
mkdir -p "$outside_update_dir"
ln -s "$outside_update_dir" "$update_dir"
if node_core_apply_application "$source_dir" "unsafe-update" 2>/dev/null; then
  printf 'FAIL: symbolic-link update directory was accepted.\n' >&2
  exit 1
fi
[[ "$(find "$outside_update_dir" -mindepth 1 -maxdepth 1 | wc -l)" == "0" ]]
rm "$update_dir"
mv "$saved_update_dir" "$update_dir"
grep -q 'new app' "$NODE_CORE_DATA_DIR/app/main.py"
grep -qx 'new-commit-123' "$NODE_CORE_DATA_DIR/runtime/node-core-commit"

# A symbolic-link backup directory must also be rejected before deployment.
backup_dir="$NODE_CORE_DATA_DIR/runtime/backups"
saved_backup_dir="$temporary_root/backup-directory-saved"
outside_backup_dir="$temporary_root/outside-backups"
mv "$backup_dir" "$saved_backup_dir"
mkdir -p "$outside_backup_dir"
ln -s "$outside_backup_dirp_dir" "$backup_dir"
if node_core_apply_application "$source_dir" "unsafe-backup" 2>/dev/null; then
  printf 'FAIL: symbolic-link backup directory was accepted.\n' >&2
  exit 1
fi
[[ "$(find "$outside_backup_dir" -mindepth 1 -maxdepth 1 | wc -l)" == "0" ]]
rm "$backup_dir"
mv "$saved_backup_dir" "$backup_dir"
grep -q 'new app' "$NODE_CORE_DATA_DIR/app/main.py"
grep -qx 'new-commit-123' "$NODE_CORE_DATA_DIR/runtime/node-core-commit"

# Reject a commit marker containing a newline before touching the application.
if node_core_apply_application "$source_dir" $'unsafe\ncommit' 2>/dev/null; then
  printf 'FAIL: multiline commit marker was accepted.\n' >&2
  exit 1
fi
grep -q 'new app' "$NODE_CORE_DATA_DIR/app/main.py"
grep -qx 'new-commit-123' "$NODE_CORE_DATA_DIR/runtime/node-core-commit"

# Reject root before touching files (mock only id inside this test process).
id() {
  printf '0\n'
}
if node_core_apply_application "$source_dir" "root-commit" 2>/dev/null; then
  printf 'FAIL: root execution was accepted.\n' >&2
  exit 1
fi
unset -f id
grep -q 'new app' "$NODE_CORE_DATA_DIR/app/main.py"

printf 'Transactional application deployment tests passed.\n'