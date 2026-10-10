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
  */fixture-update-commit.tar.gz)
    cp "$TEST_FIXTURES/fixture-update-commit.tar.gz" "$output"
    ;;
  *)
    printf 'unexpected URL in updater test: %s\n' "$url" >&2
    exit 3
    ;;
esac
FAKE_CURL
chmod +x "$TEMP_ROOT/fake-bin/curl"
export PATH="$TEMP_ROOT/fake-bin:$PATH"

# The test must run as a normal user and exercise the actual updater entry point.
test "$(id -u)" -ne 0
printf 'y\n' | "$REPOSITORY_ROOT/installer/update.sh"

# Verify the new application is installed and its commit marker is updated.
grep -q 'updated application' "$NODE_CORE_DATA_DIR/app/main.py"
grep -qx 'fixture-update-commit' "$NODE_CORE_DATA_DIR/runtime/node-core-commit"

# Verify Kubo, its repository, local storage, and configuration remain untouched.
grep -qx 'preserve local storage' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
grep -qx 'preserve IPFS repository' "$NODE_CORE_DATA_DIR/ipfs/config"
grep -qx '{"custom":"keep"}' "$NODE_CORE_DATA_DIR/config.json"
grep -q 'Kubo fixture' "$NODE_CORE_DATA_DIR/bin/ipfs"

printf 'Existing-install updater preservation tests passed.\n'
