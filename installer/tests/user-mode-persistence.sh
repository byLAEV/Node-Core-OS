#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TEMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEMP_ROOT"' EXIT

test "$(id -u)" -ne 0 || {
  printf 'ERROR: user-mode persistence tests must not run as root.\n' >&2
  exit 1
}
export HOME="$TEMP_ROOT/home"
mkdir -p "$HOME"
export NODE_CORE_DATA_DIR="$HOME/.node-core"
export PROJECT_ROOT="$REPOSITORY_ROOT"

# Existing user data is seeded before the canonical layout provisioner runs.
mkdir -p "$NODE_CORE_DATA_DIR/storage" "$NODE_CORE_DATA_DIR/ipfs"
printf 'preserve local user storage\n' > "$NODE_CORE_DATA_DIR/storage/user-data.txt"
printf '{"Identity":{"PeerID":"synthetic-user-peer"}}\n' > "$NODE_CORE_DATA_DIR/ipfs/config"
before_storage="$(sha256sum "$NODE_CORE_DATA_DIR/storage/user-data.txt" | awk '{print $1}')"
before_ipfs="$(sha256sum "$NODE_CORE_DATA_DIR/ipfs/config" | awk '{print $1}')"

# The production helper rejects root and creates only manifest-owned directories.
# shellcheck source=../lib/filesystem.sh
source "$REPOSITORY_ROOT/installer/lib/filesystem.sh"
prepare_filesystem

test "$(id -u "$NODE_CORE_DATA_DIR")" = "$(id -u)"
test "$(stat -c '%a' "$NODE_CORE_DATA_DIR")" = "700"
test "$(sha256sum "$NODE_CORE_DATA_DIR/storage/user-data.txt" | awk '{print $1}')" = "$before_storage"
test "$(sha256sum "$NODE_CORE_DATA_DIR/ipfs/config" | awk '{print $1}')" = "$before_ipfs"
test -d "$NODE_CORE_DATA_DIR/app"
test -d "$NODE_CORE_DATA_DIR/bin"
test -d "$NODE_CORE_DATA_DIR/identity"
test -d "$NODE_CORE_DATA_DIR/lobby"
test -d "$NODE_CORE_DATA_DIR/runtime"
test -d "$NODE_CORE_DATA_DIR/services"

# Symlinked persistent directories must fail closed rather than redirect writes.
unsafe_home="$TEMP_ROOT/unsafe-home"
mkdir -p "$unsafe_home/.node-core" "$TEMP_ROOT/outside-storage"
ln -s "$TEMP_ROOT/outside-storage" "$unsafe_home/.node-core/storage"
(
  export HOME="$unsafe_home"
  export NODE_CORE_DATA_DIR="$HOME/.node-core"
  set +e
  prepare_filesystem >/dev/null 2>&1
  status=$?
  set -e
  test "$status" -ne 0
)
test -z "$(find "$TEMP_ROOT/outside-storage" -mindepth 1 -print -quit)"

printf 'User-mode persistence tests passed (uid=%s).\n' "$(id -u)"
