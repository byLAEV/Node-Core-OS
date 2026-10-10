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
printf '{"sha":"1111111111111111111111111111111111111111"}\n' > "$TEST_FIXTURES/latest-commit.json"
tar -czf "$TEST_FIXTURES/1111111111111111111111111111111111111111.tar.gz" \
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
    if [[ "${FAIL_UPDATE_DOWNLOAD:-0}" == "1" ]]; then
      printf 'simulated update archive download failure\\n' >&2
      exit 22
    fi
    archive_name="${url##*/}"
    if [[ "$archive_name" == "4444444444444444444444444444444444444444.tar.gz" ]]; then
      printf 'this is not a gzip archive\\n' > "$output"
      exit 0
    fi
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
grep -qx '1111111111111111111111111111111111111111' "$NODE_CORE_DATA_DIR/runtime/node-core-commit"
printf 'Updater happy-path commit marker check passed.\\n'

# Verify Kubo, its repository, local storage, and configuration remain untouched.
grep -qx 'preserve local storage' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
grep -qx 'preserve IPFS repository' "$NODE_CORE_DATA_DIR/ipfs/config"
grep -qx '{"custom":"keep"}' "$NODE_CORE_DATA_DIR/config.json"
grep -q 'Kubo fixture' "$NODE_CORE_DATA_DIR/bin/ipfs"
printf 'Updater happy-path persistence checks passed.\\n'

# Verify that a syntactically invalid update rolls back the application.
previous_commit="$(cat "$NODE_CORE_DATA_DIR/runtime/node-core-commit")"
printf '{"sha":"2222222222222222222222222222222222222222"}\n' > "$TEST_FIXTURES/latest-commit.json"
mkdir -p "$TEMP_ROOT/bad-release/Node-Core-OS-bad/node_core"
printf 'def broken(:\n' > "$TEMP_ROOT/bad-release/Node-Core-OS-bad/main.py"
printf 'VALUE = "bad"\n' > "$TEMP_ROOT/bad-release/Node-Core-OS-bad/node_core/__init__.py"
tar -czf "$TEST_FIXTURES/2222222222222222222222222222222222222222.tar.gz" \
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


# Verify that an archive download failure leaves the current app and data intact.
previous_commit="$(cat "$NODE_CORE_DATA_DIR/runtime/node-core-commit")"
printf '{"sha":"3333333333333333333333333333333333333333"}\n' > "$TEST_FIXTURES/latest-commit.json"
set +e
printf 'y\n' | FAIL_UPDATE_DOWNLOAD=1 bash "$REPOSITORY_ROOT/installer/update.sh" > "$TEMP_ROOT/download-failure.log" 2>&1
download_status=$?
set -e
test "$download_status" -ne 0
grep -q 'Rolling back Node Core application' "$TEMP_ROOT/download-failure.log"
grep -q 'updated application' "$NODE_CORE_DATA_DIR/app/main.py"
grep -qx "$previous_commit" "$NODE_CORE_DATA_DIR/runtime/node-core-commit"
grep -qx 'preserve local storage' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
grep -qx 'preserve IPFS repository' "$NODE_CORE_DATA_DIR/ipfs/config"
grep -qx '{"custom":"keep"}' "$NODE_CORE_DATA_DIR/config.json"
grep -q 'Kubo fixture' "$NODE_CORE_DATA_DIR/bin/ipfs"

printf 'Existing-install updater download-failure rollback tests passed.\n'

# Verify that a downloaded but corrupt archive also triggers application rollback.
previous_commit="$(cat "$NODE_CORE_DATA_DIR/runtime/node-core-commit")"
printf '{"sha":"4444444444444444444444444444444444444444"}\n' > "$TEST_FIXTURES/latest-commit.json"
set +e
printf 'y\n' | bash "$REPOSITORY_ROOT/installer/update.sh" > "$TEMP_ROOT/corrupt-archive.log" 2>&1
archive_status=$?
set -e
test "$archive_status" -ne 0
grep -q 'Rolling back Node Core application' "$TEMP_ROOT/corrupt-archive.log"
grep -q 'updated application' "$NODE_CORE_DATA_DIR/app/main.py"
grep -qx "$previous_commit" "$NODE_CORE_DATA_DIR/runtime/node-core-commit"
grep -qx 'preserve local storage' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
grep -qx 'preserve IPFS repository' "$NODE_CORE_DATA_DIR/ipfs/config"
grep -qx '{"custom":"keep"}' "$NODE_CORE_DATA_DIR/config.json"
grep -q 'Kubo fixture' "$NODE_CORE_DATA_DIR/bin/ipfs"

printf 'Existing-install updater corrupt-archive rollback tests passed.\n'

# Refuse malformed release metadata before creating or applying an update.
previous_commit="$(cat "$NODE_CORE_DATA_DIR/runtime/node-core-commit")"
printf '{"sha":"not-a-full-git-commit"}\n' > "$TEST_FIXTURES/latest-commit.json"
set +e
bash "$REPOSITORY_ROOT/installer/update.sh" > "$TEMP_ROOT/invalid-metadata.log" 2>&1
metadata_status=$?
set -e
test "$metadata_status" -ne 0
grep -q 'invalid commit metadata' "$TEMP_ROOT/invalid-metadata.log"
grep -q 'updated application' "$NODE_CORE_DATA_DIR/app/main.py"
grep -qx "$previous_commit" "$NODE_CORE_DATA_DIR/runtime/node-core-commit"
grep -qx 'preserve local storage' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
grep -qx 'preserve IPFS repository' "$NODE_CORE_DATA_DIR/ipfs/config"
grep -qx '{"custom":"keep"}' "$NODE_CORE_DATA_DIR/config.json"
grep -q 'Kubo fixture' "$NODE_CORE_DATA_DIR/bin/ipfs"

printf 'Existing-install updater invalid-release-metadata tests passed.\n'


# If rollback itself fails, keep the recovery backup and report the failure honestly.
printf '{"sha":"5555555555555555555555555555555555555555"}\n' > "$TEST_FIXTURES/latest-commit.json"
mkdir -p "$TEMP_ROOT/rollback-failure-release/Node-Core-OS-rollback-failure/node_core"
printf 'def broken(:\n' > "$TEMP_ROOT/rollback-failure-release/Node-Core-OS-rollback-failure/main.py"
printf 'VALUE = "broken"\n' > "$TEMP_ROOT/rollback-failure-release/Node-Core-OS-rollback-failure/node_core/__init__.py"
tar -czf "$TEST_FIXTURES/5555555555555555555555555555555555555555.tar.gz" \
  -C "$TEMP_ROOT/rollback-failure-release" Node-Core-OS-rollback-failure

REAL_CP="$(command -v cp)"
cat > "$TEMP_ROOT/fake-bin/cp" <<'FAKE_CP'
#!/usr/bin/env bash
set -euo pipefail
source_path="${@: -2:1}"
destination_path="${@: -1}"
if [[ "$source_path" == */app-backup && "$destination_path" == "$NODE_CORE_DATA_DIR/app" ]]; then
  printf 'simulated rollback copy failure\n' >&2
  exit 1
fi
exec "$REAL_CP" "$@"
FAKE_CP
chmod +x "$TEMP_ROOT/fake-bin/cp"
export REAL_CP
previous_commit="$(cat "$NODE_CORE_DATA_DIR/runtime/node-core-commit")"
set +e
printf 'y\n' | bash "$REPOSITORY_ROOT/installer/update.sh" > "$TEMP_ROOT/rollback-failure.log" 2>&1
rollback_failure_status=$?
set -e
test "$rollback_failure_status" -ne 0
grep -q 'ERROR: Node Core application rollback failed' "$TEMP_ROOT/rollback-failure.log"
grep -q 'Recovery files were retained for manual recovery' "$TEMP_ROOT/rollback-failure.log"
! grep -q 'Node Core application and commit marker restored' "$TEMP_ROOT/rollback-failure.log"
test -d "$NODE_CORE_DATA_DIR/runtime/update/app-backup"
test -f "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-backup"
test -f "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-state"
grep -qx "$previous_commit" "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-backup"
grep -qx 'preserve local storage' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
grep -qx 'preserve IPFS repository' "$NODE_CORE_DATA_DIR/ipfs/config"
grep -qx '{"custom":"keep"}' "$NODE_CORE_DATA_DIR/config.json"
grep -q 'Kubo fixture' "$NODE_CORE_DATA_DIR/bin/ipfs"
rm -f "$TEMP_ROOT/fake-bin/cp"
# A later updater invocation must not erase recovery artifacts left by a failed rollback.
set +e
bash "$REPOSITORY_ROOT/installer/update.sh" > "$TEMP_ROOT/pending-recovery.log" 2>&1
pending_recovery_status=$?
set -e
test "$pending_recovery_status" -ne 0
grep -q 'A previous update left recovery files that require inspection' "$TEMP_ROOT/pending-recovery.log"
grep -q 'Refusing to start another update' "$TEMP_ROOT/pending-recovery.log"
test -d "$NODE_CORE_DATA_DIR/runtime/update/app-backup"
test -f "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-backup"
test -f "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-state"
grep -qx "$previous_commit" "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-backup"

printf 'Existing-install updater rollback-failure recovery retention test passed.\n'

printf 'Existing-install updater preservation and rollback tests passed.\n'
