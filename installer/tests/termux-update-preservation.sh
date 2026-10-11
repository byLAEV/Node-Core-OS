#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEMP_ROOT"' EXIT

export HOME="$TEMP_ROOT/home"
export NODE_CORE_DATA_DIR="$HOME/.node-core"
export PREFIX="$TEMP_ROOT/termux-prefix"
export TERMUX_VERSION="test-termux"
export TEST_FIXTURES="$TEMP_ROOT/fixtures"
mkdir -p "$HOME" "$TEST_FIXTURES" \
  "$NODE_CORE_DATA_DIR/app/installer" \
  "$NODE_CORE_DATA_DIR/app/node_core" \
  "$NODE_CORE_DATA_DIR/storage" \
  "$NODE_CORE_DATA_DIR/ipfs" \
  "$NODE_CORE_DATA_DIR/bin" \
  "$NODE_CORE_DATA_DIR/runtime" \
  "$PREFIX/bin" \
  "$TEMP_ROOT/fake-bin"

test "$(id -u)" -ne 0

# Seed an existing installation with an Android-compatible Kubo executable.
printf 'print("existing Node Core application")\n' > "$NODE_CORE_DATA_DIR/app/main.py"
printf 'VALUE = "existing"\n' > "$NODE_CORE_DATA_DIR/app/node_core/__init__.py"
cp "$REPOSITORY_ROOT/installer/update.sh" "$NODE_CORE_DATA_DIR/app/installer/update.sh"
printf 'preserve Termux local storage\n' > "$NODE_CORE_DATA_DIR/storage/user-data.txt"
printf 'preserve Termux IPFS repository\n' > "$NODE_CORE_DATA_DIR/ipfs/config"
printf '{"ipfs_executable":"%s","custom":"keep"}\n' \
  "$NODE_CORE_DATA_DIR/bin/ipfs" > "$NODE_CORE_DATA_DIR/config.json"
printf '#!/usr/bin/env bash\necho "old bundled Kubo fixture"\n' > "$NODE_CORE_DATA_DIR/bin/ipfs"
chmod +x "$NODE_CORE_DATA_DIR/bin/ipfs"
printf '#!/usr/bin/env bash\nif [[ "${1:-}" == "version" ]]; then echo "kubo version test"; exit 0; fi\nexit 2\n' > "$PREFIX/bin/ipfs"
chmod +x "$PREFIX/bin/ipfs"
printf 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n' > "$NODE_CORE_DATA_DIR/runtime/node-core-commit"
printf '{"sha":"5555555555555555555555555555555555555555"}\n' > "$TEST_FIXTURES/latest-commit.json"

# Build a local release archive to exercise the actual update path without network access.
mkdir -p "$TEST_FIXTURES/release/Node-Core-OS-test/node_core" \
  "$TEST_FIXTURES/release/Node-Core-OS-test/installer" \
  "$TEST_FIXTURES/release/Node-Core-OS-test/applications/hashpaper/hashpaper" \
  "$TEST_FIXTURES/release/Node-Core-OS-test/applications/hashpaper/tests"
printf 'print("updated Node Core application")\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/main.py"
printf 'VALUE = "updated"\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/node_core/__init__.py"
cp "$REPOSITORY_ROOT/installer/update.sh" "$TEST_FIXTURES/release/Node-Core-OS-test/installer/update.sh"
printf 'print("updated HashPaper")\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/hashpaper/main.py"
printf 'VALUE = "updated HashPaper CLI"\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/hashpaper/hashpaper/cli.py"
cat > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/hashpaper/tests/test_smoke.py" <<'PY'
import unittest

class UpdaterFixtureSmokeTest(unittest.TestCase):
    def test_fixture_release_is_testable(self):
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
PY
tar -czf "$TEST_FIXTURES/5555555555555555555555555555555555555555.tar.gz" \
  -C "$TEST_FIXTURES/release" Node-Core-OS-test

cat > "$TEMP_ROOT/fake-bin/curl" <<'FAKE_CURL'
#!/usr/bin/env bash
set -euo pipefail
output=""
url=""
while (($#)); do
  case "$1" in
    --output) output="$2"; shift 2 ;;
    http://*|https://*) url="$1"; shift ;;
    *) shift ;;
  esac
done
[[ -n "$output" && -n "$url" ]] || exit 2
case "$url" in
  */commits/main) cp "$TEST_FIXTURES/latest-commit.json" "$output" ;;
  */archive/5555555555555555555555555555555555555555.tar.gz) cp "$TEST_FIXTURES/5555555555555555555555555555555555555555.tar.gz" "$output" ;;
  *) printf 'unexpected URL in Termux updater test: %s\n' "$url" >&2; exit 3 ;;
esac
FAKE_CURL
chmod +x "$TEMP_ROOT/fake-bin/curl"
export PATH="$TEMP_ROOT/fake-bin:$PATH"

printf "y\n" | bash "$REPOSITORY_ROOT/installer/update.sh"

python3 - "$NODE_CORE_DATA_DIR/config.json" "$PREFIX/bin/ipfs" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
expected_ipfs = sys.argv[2]
config = json.loads(config_path.read_text(encoding="utf-8"))
assert config["ipfs_executable"] == expected_ipfs, config
assert config["custom"] == "keep", config
PY

grep -qx 'preserve Termux local storage' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
grep -qx 'preserve Termux IPFS repository' "$NODE_CORE_DATA_DIR/ipfs/config"
grep -q 'old bundled Kubo fixture' "$NODE_CORE_DATA_DIR/bin/ipfs"
grep -qx '5555555555555555555555555555555555555555' "$NODE_CORE_DATA_DIR/runtime/node-core-commit"
grep -q 'updated Node Core application' "$NODE_CORE_DATA_DIR/app/main.py"
test -x "$NODE_CORE_DATA_DIR/bin/node-core"
test -x "$NODE_CORE_DATA_DIR/bin/node-core-update"

# An interrupted cleanup can leave marker files after the app backup has gone.
# The updater must validate the installed app, archive the markers, and continue.
printf 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n' > "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-backup"
printf 'present\n' > "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-state"
test ! -e "$NODE_CORE_DATA_DIR/runtime/update/app-backup"
bash "$REPOSITORY_ROOT/installer/update.sh" > "$TEMP_ROOT/stale-cleanup-recovery.log" 2>&1
grep -q 'Installed application validation passed' "$TEMP_ROOT/stale-cleanup-recovery.log"
grep -q 'Recovery markers archived at:' "$TEMP_ROOT/stale-cleanup-recovery.log"
test ! -e "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-backup"
test ! -e "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-state"
recovery_archive="$(find "$NODE_CORE_DATA_DIR/runtime" -maxdepth 1 -type d -name 'update-recovery-*' -print -quit)"
test -n "$recovery_archive"
test -f "$recovery_archive/commit-marker-backup"
test -f "$recovery_archive/commit-marker-state"
test -f "$recovery_archive/RECOVERY.txt"
grep -qx '5555555555555555555555555555555555555555' "$NODE_CORE_DATA_DIR/runtime/node-core-commit"
grep -qx 'preserve Termux local storage' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
grep -qx 'preserve Termux IPFS repository' "$NODE_CORE_DATA_DIR/ipfs/config"

printf 'Termux updater stale-cleanup recovery test passed.\n'

printf 'Termux updater real-update and data-preservation tests passed.\n'
