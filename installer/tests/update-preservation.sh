#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEMP_ROOT"' EXIT

export HOME="$TEMP_ROOT/home"
export NODE_CORE_DATA_DIR="$HOME/.node-core"
export TEST_FIXTURES="$TEMP_ROOT/fixtures"
mkdir -p "$HOME" "$TEST_FIXTURES" \
  "$NODE_CORE_DATA_DIR/app/node_core" \
  "$NODE_CORE_DATA_DIR/storage" \
  "$NODE_CORE_DATA_DIR/ipfs" \
  "$NODE_CORE_DATA_DIR/bin" \
  "$NODE_CORE_DATA_DIR/runtime" \
  "$TEMP_ROOT/fake-bin"

# Seed an existing, unprivileged installation and persistent user data.
printf 'print("old application")\n' > "$NODE_CORE_DATA_DIR/app/main.py"
printf 'VALUE = "old"\n' > "$NODE_CORE_DATA_DIR/app/node_core/__init__.py"
printf 'preserve local storage\n' > "$NODE_CORE_DATA_DIR/storage/user-data.txt"
printf 'preserve IPFS repository\n' > "$NODE_CORE_DATA_DIR/ipfs/config"
printf '{"custom":"keep"}\n' > "$NODE_CORE_DATA_DIR/config.json"
printf '#!/usr/bin/env bash\necho "Kubo fixture"\n' > "$NODE_CORE_DATA_DIR/bin/ipfs"
chmod +x "$NODE_CORE_DATA_DIR/bin/ipfs"

# Create a deterministic release archive. The fake curl prevents network access.
release_root="$TEMP_ROOT/release-root"
mkdir -p "$release_root/Node-Core-OS-fixture/node_core"
printf 'print("updated application")\n' > "$release_root/Node-Core-OS-fixture/main.py"
printf 'VALUE = "updated"\n' > "$release_root/Node-Core-OS-fixture/node_core/__init__.py"
printf '{"sha":"fixture-update-commit"}\n' > "$TEST_FIXTURES/latest-commit.json"
tar -czf "$TEST_FIXTURES/fixture-update-commit.tar.gz" \
  -C "$release_root" Node-Core-OS-fixture

cat > "$TEMP_ROOT/fake-bin/curl" <<'FAKE_CURL'
#!/usr/bin/env bash
set -euo pipefail
output=""
url=""
while (($#)); do
  case "$1" in
    --output)
      output="$2"
      shift 2
      ;;
    http://*|https://*)
      url="$1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done
[[ -n "$output" && -n "$url" ]] || {
  printf 'fake curl received unsupported arguments\n' >&2
  exit 2
}
case "$url" in
  */commits/main)
    cp "$TEST_FIXTURES/latest-commit.json" "$output"
    ;;
  */archive/*.tar.gz)
    archive_name="${url##*/}"
    archive="$TEST_FIXTURES/$archive_name"
    [[ -f "$archive" ]] || {
      printf 'missing updater archive fixture: %s\\n' "$archive" >&2
      exit 4
    }
    cp "$archive" "$output"
    ;;
  *)
    printf 'unexpected URL in updater test: %s\\n' "$url" >&2
    exit 3
    ;;
esac
FAKE_CURL
chmod +x "$TEMP_ROOT/fake-bin/curl"
export PATH="$TEMP_ROOT/fake-bin:$PATH"

# The test must run as a normal user and exercise the actual updater entry point.
test "$(id -u)" -ne 0
printf 'y\n' | bash "$REPOSITORY_ROOT/installer/update.sh"

# Verify the new application is installed and its commit marker is updated.
grep -q 'updated application' "$NODE_CORE_DATA_DIR/app/main.py"
printf 'Updater happy-path application check passed.\\n'
grep -qx 'fixture-update-commit' "$NODE_CORE_DATA_DIR/runtime/node-core-commit"
printf 'Updater happy-path commit marker check passed.\\n'

# Verify Kubo, its repository, local storage, and configuration remain untouched.
grep -qx 'preserve local storage' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
grep -qx 'preserve IPFS repository' "$NODE_CORE_DATA_DIR/ipfs/config"
grep -qx '{"custom":"keep"}' "$NODE_CORE_DATA_DIR/config.json"
grep -q 'Kubo fixture' "$NODE_CORE_DATA_DIR/bin/ipfs"
printf 'Updater happy-path persistence checks passed.\\n'

# Verify that a syntactically invalid update rolls back the application.
previous_commit="$(cat "$NODE_CORE_DATA_DIR/runtime/node-core-commit")"
printf '{"sha":"fixture-bad-update"}\n' > "$TEST_FIXTURES/latest-commit.json"
mkdir -p "$TEMP_ROOT/bad-release/Node-Core-OS-bad/node_core"
printf 'def broken(:\n' > "$TEMP_ROOT/bad-release/Node-Core-OS-bad/main.py"
printf 'VALUE = "bad"\n' > "$TEMP_ROOT/bad-release/Node-Core-OS-bad/node_core/__init__.py"
tar -czf "$TEST_FIXTURES/fixture-bad-update.tar.gz" \
  -C "$TEMP_ROOT/bad-release" Node-Core-OS-bad

set +e
printf 'y\n' | bash "$REPOSITORY_ROOT/installer/update.sh" > "$TEMP_ROOT/rollback.log" 2>&1
update_status=$?
set -e
test "$update_status" -ne 0
grep -q 'Rolling back Node Core application' "$TEMP_ROOT/rollback.log"
grep -q 'updated application' "$NODE_CORE_DATA_DIR/app/main.py"
grep -qx "$previous_commit" "$NODE_CORE_DATA_DIR/runtime/node-core-commit"

# A failed update must also preserve all persistent user data and Kubo assets.
grep -qx 'preserve local storage' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
grep -qx 'preserve IPFS repository' "$NODE_CORE_DATA_DIR/ipfs/config"
grep -qx '{"custom":"keep"}' "$NODE_CORE_DATA_DIR/config.json"
grep -q 'Kubo fixture' "$NODE_CORE_DATA_DIR/bin/ipfs"

printf 'Existing-install updater preservation and rollback tests passed.\n'
