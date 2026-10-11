#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEMP_ROOT"' EXIT

test "$(id -u)" -ne 0
export HOME="$TEMP_ROOT/home"
export NODE_CORE_DATA_DIR="$HOME/.node-core"
export HASH_PAPER_REPOSITORY="fixture/hashpaper"
export HASH_PAPER_BRANCH="main"
export TEST_FIXTURES="$TEMP_ROOT/fixtures"
mkdir -p "$HOME" "$NODE_CORE_DATA_DIR/app/node_core" "$NODE_CORE_DATA_DIR/app/applications/hashpaper/hashpaper" \
  "$NODE_CORE_DATA_DIR/hashpaper/documents" "$NODE_CORE_DATA_DIR/hashpaper/packages" \
  "$NODE_CORE_DATA_DIR/hashpaper/records" "$NODE_CORE_DATA_DIR/storage" \
  "$NODE_CORE_DATA_DIR/ipfs" "$NODE_CORE_DATA_DIR/runtime" "$NODE_CORE_DATA_DIR/bin" \
  "$TEST_FIXTURES/release/HashPaper-Release/applications/hashpaper/hashpaper" \
  "$TEST_FIXTURES/release/HashPaper-Release/applications/hashpaper/tests" "$TEMP_ROOT/fake-bin"

printf 'print("existing core")\n' > "$NODE_CORE_DATA_DIR/app/main.py"
printf 'VALUE = "core-preserved"\n' > "$NODE_CORE_DATA_DIR/app/node_core/runtime.py"
printf '0.1.0\n' > "$NODE_CORE_DATA_DIR/app/applications/hashpaper/VERSION"
printf 'print("old HashPaper")\n' > "$NODE_CORE_DATA_DIR/app/applications/hashpaper/main.py"
printf 'VALUE = "old"\n' > "$NODE_CORE_DATA_DIR/app/applications/hashpaper/hashpaper/cli.py"
printf 'preserve document\n' > "$NODE_CORE_DATA_DIR/hashpaper/documents/original.md"
printf 'preserve package\n' > "$NODE_CORE_DATA_DIR/hashpaper/packages/package.json"
printf 'preserve receipt\n' > "$NODE_CORE_DATA_DIR/hashpaper/records/receipt.json"
printf 'preserve local storage\n' > "$NODE_CORE_DATA_DIR/storage/user-data.txt"
printf 'preserve IPFS repository\n' > "$NODE_CORE_DATA_DIR/ipfs/config"

printf '0.3.0\n' > "$TEST_FIXTURES/release/HashPaper-Release/applications/hashpaper/VERSION"
printf 'print("updated HashPaper")\n' > "$TEST_FIXTURES/release/HashPaper-Release/applications/hashpaper/main.py"
printf 'VALUE = "new"\n' > "$TEST_FIXTURES/release/HashPaper-Release/applications/hashpaper/hashpaper/cli.py"
cat > "$TEST_FIXTURES/release/HashPaper-Release/applications/hashpaper/tests/test_smoke.py" <<'PY'
import unittest

class UpdaterSmokeTest(unittest.TestCase):
    def test_release_fixture(self):
        self.assertEqual(2 + 2, 4)
PY
tar -czf "$TEST_FIXTURES/release.tar.gz" -C "$TEST_FIXTURES/release" HashPaper-Release
printf '{"sha":"5555555555555555555555555555555555555555"}\n' > "$TEST_FIXTURES/latest-commit.json"

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
  */repos/fixture/hashpaper/commits/main) cp "$TEST_FIXTURES/latest-commit.json" "$output" ;;
  */fixture/hashpaper/archive/5555555555555555555555555555555555555555.tar.gz) cp "$TEST_FIXTURES/release.tar.gz" "$output" ;;
  *) printf 'Unexpected URL in HashPaper updater test: %s\n' "$url" >&2; exit 3 ;;
esac
FAKE_CURL
chmod +x "$TEMP_ROOT/fake-bin/curl"
export PATH="$TEMP_ROOT/fake-bin:$PATH"

printf 'y\n' | bash "$REPOSITORY_ROOT/installer/hashpaper-update.sh"

grep -qx '0.3.0' "$NODE_CORE_DATA_DIR/app/applications/hashpaper/VERSION"
grep -q 'updated HashPaper' "$NODE_CORE_DATA_DIR/app/applications/hashpaper/main.py"
grep -q 'existing core' "$NODE_CORE_DATA_DIR/app/main.py"
grep -qx 'preserve document' "$NODE_CORE_DATA_DIR/hashpaper/documents/original.md"
grep -qx 'preserve package' "$NODE_CORE_DATA_DIR/hashpaper/packages/package.json"
grep -qx 'preserve receipt' "$NODE_CORE_DATA_DIR/hashpaper/records/receipt.json"
grep -qx 'preserve local storage' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
grep -qx 'preserve IPFS repository' "$NODE_CORE_DATA_DIR/ipfs/config"
test ! -e "$NODE_CORE_DATA_DIR/runtime/hashpaper-update"
test ! -e "$NODE_CORE_DATA_DIR/runtime/hashpaper-update.lock"

printf 'HashPaper-only updater and persistent-data preservation test passed.\n'
