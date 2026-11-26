#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../lib/detect.sh
source "$REPOSITORY_ROOT/installer/lib/detect.sh"

temporary_root="$(mktemp -d)"
trap 'rm -rf "$temporary_root"' EXIT
export HOME="$temporary_root/home"
export NODE_CORE_DATA_DIR="$HOME/.node-core"
mkdir -p "$HOME" "$NODE_CORE_DATA_DIR/app/node_core" "$NODE_CORE_DATA_DIR/bin" \
  "$NODE_CORE_DATA_DIR/storage" "$NODE_CORE_DATA_DIR/ipfs" "$NODE_CORE_DATA_DIR/runtime"
printf 'print("test")\n' > "$NODE_CORE_DATA_DIR/app/main.py"
printf 'test\n' > "$NODE_CORE_DATA_DIR/storage/preserved.txt"
printf '{"data_dir":"%s"}\n' "$NODE_CORE_DATA_DIR" > "$NODE_CORE_DATA_DIR/config.json"
printf 'test repository\n' > "$NODE_CORE_DATA_DIR/ipfs/config"
printf 'abcdef123456\n' > "$NODE_CORE_DATA_DIR/runtime/node-core-commit"
printf '#!/usr/bin/env bash\nprintf "Kubo\n"\n' > "$NODE_CORE_DATA_DIR/bin/ipfs"
printf '#!/usr/bin/env bash\nexit 0\n' > "$NODE_CORE_DATA_DIR/bin/node-core"
chmod +x "$NODE_CORE_DATA_DIR/bin/ipfs" "$NODE_CORE_DATA_DIR/bin/node-core"

before_hash="$(sha256sum "$NODE_CORE_DATA_DIR/storage/preserved.txt" "$NODE_CORE_DATA_DIR/ipfs/config" "$NODE_CORE_DATA_DIR/config.json")"
before_files="$(find "$NODE_CORE_DATA_DIR" -type f -print | sort)"

report="$(node_core_detect_installation)"
grep -qx 'application=present' <<<"$report"
grep -qx 'launcher=present' <<<"$report"
grep -qx 'update_launcher=missing' <<<"$report"
grep -qx 'kubo=present' <<<"$report"
grep -qx 'ipfs_repository=present' <<<"$report"
grep -qx 'local_storage=present' <<<"$report"
grep -qx 'configuration=valid' <<<"$report"
grep -qx 'manifest=missing' <<<"$report"
grep -qx 'installed_commit=abcdef123456' <<<"$report"

after_hash="$(sha256sum "$NODE_CORE_DATA_DIR/storage/preserved.txt" "$NODE_CORE_DATA_DIR/ipfs/config" "$NODE_CORE_DATA_DIR/config.json")"
after_files="$(find "$NODE_CORE_DATA_DIR" -type f -print | sort)"
[[ "$before_hash" == "$after_hash" ]]
[[ "$before_files" == "$after_files" ]]

# The detector must also classify incomplete application/configuration states.
rm -f "$NODE_CORE_DATA_DIR/app/main.py"
printf 'not json\n' > "$NODE_CORE_DATA_DIR/config.json"
report="$(node_core_detect_installation)"
grep -qx 'application=incomplete' <<<"$report"
grep -qx 'configuration=invalid' <<<"$report"

printf 'Installer state detection tests passed.\n'
