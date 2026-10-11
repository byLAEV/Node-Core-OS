#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
INSTALLER="$REPOSITORY_ROOT/installer/hashpaper-install.sh"
temporary_root="$(mktemp -d)"
trap 'rm -rf "$temporary_root"' EXIT

export HOME="$temporary_root/home"
export NODE_CORE_DATA_DIR="$HOME/.node-core"
mkdir -p "$HOME" "$NODE_CORE_DATA_DIR/app/applications/hashpaper" "$NODE_CORE_DATA_DIR/app/installer/lib" "$NODE_CORE_DATA_DIR/hashpaper/documents" "$NODE_CORE_DATA_DIR/hashpaper/proofs" "$NODE_CORE_DATA_DIR/hashpaper/packages" "$NODE_CORE_DATA_DIR/hashpaper/records" "$NODE_CORE_DATA_DIR/storage" "$NODE_CORE_DATA_DIR/ipfs"
cat > "$NODE_CORE_DATA_DIR/app/installer/lib/opentimestamps.sh" <<'HELPER'
ensure_opentimestamps_client() { printf 'OTS helper called\n'; }
HELPER
printf '#!/usr/bin/env python3\nprint("synthetic HashPaper entry")\n' > "$NODE_CORE_DATA_DIR/app/applications/hashpaper/main.py"
printf '0.3.3\n' > "$NODE_CORE_DATA_DIR/app/applications/hashpaper/VERSION"
printf 'synthetic document\n' > "$NODE_CORE_DATA_DIR/hashpaper/documents/original.md"
printf 'synthetic proof\n' > "$NODE_CORE_DATA_DIR/hashpaper/proofs/original.md.ots"
printf 'synthetic package\n' > "$NODE_CORE_DATA_DIR/hashpaper/packages/original.json"
printf 'synthetic record\n' > "$NODE_CORE_DATA_DIR/hashpaper/records/original.json"
printf 'synthetic storage\n' > "$NODE_CORE_DATA_DIR/storage/user-data.txt"
printf 'synthetic Kubo config\n' > "$NODE_CORE_DATA_DIR/ipfs/config"

before="$(find "$NODE_CORE_DATA_DIR/hashpaper" "$NODE_CORE_DATA_DIR/storage" "$NODE_CORE_DATA_DIR/ipfs" -type f -exec sha256sum {} + | sort)"
bash "$INSTALLER"
test -x "$NODE_CORE_DATA_DIR/bin/hashpaper"
for directory in documents proofs ipfs packages records; do
  test -d "$NODE_CORE_DATA_DIR/hashpaper/$directory"
  test "$(stat -c '%a' "$NODE_CORE_DATA_DIR/hashpaper/$directory")" = "700"
done
grep -q 'export NODE_CORE_DATA_DIR' "$NODE_CORE_DATA_DIR/bin/hashpaper"
grep -q 'opentimestamps-venv/bin:$PATH' "$NODE_CORE_DATA_DIR/bin/hashpaper"
grep -q 'exec python3 "$HASH_PAPER_ENTRY" "$@"' "$NODE_CORE_DATA_DIR/bin/hashpaper"
after="$(find "$NODE_CORE_DATA_DIR/hashpaper" "$NODE_CORE_DATA_DIR/storage" "$NODE_CORE_DATA_DIR/ipfs" -type f -exec sha256sum {} + | sort)"
test "$before" = "$after"

# A pre-existing launcher symlink must not be followed or overwritten.
printf 'keep symlink target unchanged\n' > "$temporary_root/launcher-target"
rm -f "$NODE_CORE_DATA_DIR/bin/hashpaper"
ln -s "$temporary_root/launcher-target" "$NODE_CORE_DATA_DIR/bin/hashpaper"
if bash "$INSTALLER" >/dev/null 2>&1; then
  printf 'Installer unexpectedly overwrote a symbolic-link launcher.\n' >&2
  exit 1
fi
grep -qx 'keep symlink target unchanged' "$temporary_root/launcher-target"
rm "$NODE_CORE_DATA_DIR/bin/hashpaper"

if NODE_CORE_DATA_DIR="$temporary_root/outside/.node-core" bash "$INSTALLER" >/dev/null 2>&1; then
  printf 'Installer unexpectedly accepted a data directory outside HOME.\n' >&2
  exit 1
fi

printf 'HashPaper user installer tests: OK\n'
