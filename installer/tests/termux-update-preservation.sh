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

# The updater may replace only app/. The technical NODE ID, entity registry,
# staged Bitcoin proof, local storage and Kubo repository must remain byte-identical.
mkdir -p "$NODE_CORE_DATA_DIR/identity/private" "$NODE_CORE_DATA_DIR/lobby" \
  "$NODE_CORE_DATA_DIR/ipfs/blocks/aa" "$NODE_CORE_DATA_DIR/ipfs/datastore"
printf '{"schema_version":1,"algorithm":"Ed25519","node_id":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","public_key":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}\n' > "$NODE_CORE_DATA_DIR/identity/node.json"
printf 'SYNTHETIC_NODE_PRIVATE_KEY_FIXTURE\n' > "$NODE_CORE_DATA_DIR/identity/private/node.key"
printf '{"schema_version":1,"entities":[{"entity_id":"12345678-1234-5678-1234-567812345678","entity_type":"person","display_name":"Synthetic Termux Identity","status":"active","identity_assurance":"declared","node_links":[{"node_id":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","relationship":"controlled_by","status":"declared"}],"evidence_references":[]}]}\n' > "$NODE_CORE_DATA_DIR/identity/entity-registry.json"
printf '{"schema_version":1,"identity_id":"synthetic-termux-profile","full_name":"Synthetic Termux Identity","identity_assurance":"declared","node_id":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}\n' > "$NODE_CORE_DATA_DIR/identity/profile.json"
printf '{"schema_version":1,"full_name":"Synthetic Termux Identity","private_key_storage":false,"bitcoin":{"network":"mainnet","address_type":"p2wpkh","address":"bc1qsynthetic"},"entity_id":"12345678-1234-5678-1234-567812345678"}\n' > "$NODE_CORE_DATA_DIR/lobby/bitcoin-identity-pending.json"
printf 'synthetic Kubo block payload\n' > "$NODE_CORE_DATA_DIR/ipfs/blocks/aa/fixture-block"
printf 'synthetic Kubo datastore payload\n' > "$NODE_CORE_DATA_DIR/ipfs/datastore/fixture-data"
printf 'volatile API marker\n' > "$NODE_CORE_DATA_DIR/ipfs/api"
printf 'volatile repository lock\n' > "$NODE_CORE_DATA_DIR/ipfs/repo.lock"
printf 'volatile datastore lock\n' > "$NODE_CORE_DATA_DIR/ipfs/datastore/LOCK"
chmod 700 "$NODE_CORE_DATA_DIR/identity" "$NODE_CORE_DATA_DIR/identity/private" "$NODE_CORE_DATA_DIR/lobby"
chmod 600 "$NODE_CORE_DATA_DIR/identity/node.json" "$NODE_CORE_DATA_DIR/identity/private/node.key" "$NODE_CORE_DATA_DIR/identity/entity-registry.json" "$NODE_CORE_DATA_DIR/lobby/bitcoin-identity-pending.json"
sha256sum \
  "$NODE_CORE_DATA_DIR/identity/node.json" \
  "$NODE_CORE_DATA_DIR/identity/private/node.key" \
  "$NODE_CORE_DATA_DIR/identity/profile.json" \
  "$NODE_CORE_DATA_DIR/identity/entity-registry.json" \
  "$NODE_CORE_DATA_DIR/lobby/bitcoin-identity-pending.json" \
  > "$TEST_FIXTURES/identity-state-before.sha256"

assert_identity_and_data_preserved() {
  sha256sum --check "$TEST_FIXTURES/identity-state-before.sha256"
  grep -qx 'preserve Termux local storage' "$NODE_CORE_DATA_DIR/storage/user-data.txt"
  grep -qx 'preserve Termux IPFS repository' "$NODE_CORE_DATA_DIR/ipfs/config"
  test -x "$NODE_CORE_DATA_DIR/bin/ipfs"
}

cat > "$TEST_FIXTURES/persistence-check.py" <<'PY'
import json
import stat
import sys
from pathlib import Path

from node_core.persistence_integrity import (
    capture_persistence_manifest,
    compare_persistence_manifests,
    write_persistence_manifest,
)

action, first, second = sys.argv[1:4]
if action == "capture":
    root = Path(first)
    output = Path(second)
    manifest = capture_persistence_manifest(root, kubo_repo=root / "ipfs")
    expected = {
        "node_identity",
        "profile",
        "entity_registry",
        "local_storage",
        "kubo_ipfs",
    }
    if set(manifest["scopes"]) != expected:
        raise SystemExit("Persistence manifest does not cover all five required scopes.")
    write_persistence_manifest(output, manifest)
    if stat.S_IMODE(output.stat().st_mode) != 0o600:
        raise SystemExit("Private persistence manifest permissions are not 0600.")
    print("Private SHA-256 persistence manifest captured for all five scopes.")
elif action == "compare":
    before = json.loads(Path(first).read_text(encoding="utf-8"))
    after = json.loads(Path(second).read_text(encoding="utf-8"))
    result = compare_persistence_manifests(before, after)
    if not result["matches"]:
        print(json.dumps(result, sort_keys=True))
        raise SystemExit("Persistent data changed across update or recovery.")
    print("All five SHA-256 persistence scopes match: PASS.")
else:
    raise SystemExit("Unknown persistence-check action.")
PY

PYTHONPATH="$REPOSITORY_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  python3 "$TEST_FIXTURES/persistence-check.py" capture \
  "$NODE_CORE_DATA_DIR" "$TEST_FIXTURES/persistence-before.json"

printf '{"sha":"5555555555555555555555555555555555555555"}\n' > "$TEST_FIXTURES/latest-commit.json"

# Simulate a venv created by the older installer without system-site-packages.
python3 -m venv "$NODE_CORE_DATA_DIR/runtime/node-core-venv"
grep -q '^include-system-site-packages = false$' "$NODE_CORE_DATA_DIR/runtime/node-core-venv/pyvenv.cfg"

# Build a local release archive to exercise the actual update path without network access.
mkdir -p "$TEST_FIXTURES/release/Node-Core-OS-test/node_core" \
  "$TEST_FIXTURES/release/Node-Core-OS-test/tests" \
  "$TEST_FIXTURES/release/Node-Core-OS-test/installer" \
  "$TEST_FIXTURES/release/Node-Core-OS-test/applications/hashpaper/hashpaper" \
  "$TEST_FIXTURES/release/Node-Core-OS-test/applications/hashpaper/tests" \
  "$TEST_FIXTURES/release/Node-Core-OS-test/applications/p2p_contracts/p2p_contracts" \
  "$TEST_FIXTURES/release/Node-Core-OS-test/applications/p2p_contracts/tests" \
  "$TEST_FIXTURES/release/Node-Core-OS-test/docs" \
  "$TEST_FIXTURES/release/Node-Core-OS-test/.github/workflows"
printf 'print("updated Node Core application")\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/main.py"
printf '1.2.6\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/VERSION"
# Keep the offline release fixture dependency-free while exercising the updater.
: > "$TEST_FIXTURES/release/Node-Core-OS-test/requirements.txt"
# A valid release fixture must contain importable core tests because the updater
# runs unittest discovery before activating any downloaded application.
: > "$TEST_FIXTURES/release/Node-Core-OS-test/tests/__init__.py"
cat > "$TEST_FIXTURES/release/Node-Core-OS-test/tests/test_core_fixture.py" <<'PY'
import unittest

class CoreFixtureTest(unittest.TestCase):
    def test_fixture_is_importable(self):
        self.assertTrue(True)
PY
printf '0.3.0\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/hashpaper/VERSION"
printf 'VALUE = "updated"\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/node_core/__init__.py"
cp "$REPOSITORY_ROOT/installer/update.sh" "$TEST_FIXTURES/release/Node-Core-OS-test/installer/update.sh"
printf 'print("updated HashPaper")\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/hashpaper/main.py"
printf 'VALUE = "updated HashPaper CLI"\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/hashpaper/hashpaper/cli.py"
printf 'print("fixture P2P Contracts")\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/p2p_contracts/main.py"
printf 'VALUE = "fixture P2P CLI"\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/p2p_contracts/p2p_contracts/cli.py"
printf 'VALUE = "fixture P2P service"\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/p2p_contracts/p2p_contracts/service.py"
printf 'VALUE = "fixture P2P propagation"\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/p2p_contracts/p2p_contracts/propagation.py"
cp "$REPOSITORY_ROOT/applications/p2p_contracts/genesis-manifest.json" \
  "$TEST_FIXTURES/release/Node-Core-OS-test/applications/p2p_contracts/genesis-manifest.json"
cp "$REPOSITORY_ROOT/applications/p2p_contracts/p2p_contracts/genesis.py" \
  "$TEST_FIXTURES/release/Node-Core-OS-test/applications/p2p_contracts/p2p_contracts/genesis.py"
cat > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/p2p_contracts/tests/test_service.py" <<'PY'
import unittest
class P2PServiceFixtureTest(unittest.TestCase):
    def test_fixture(self):
        self.assertTrue(True)
PY
cat > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/p2p_contracts/tests/test_propagation.py" <<'PY'
import unittest
class P2PPropagationFixtureTest(unittest.TestCase):
    def test_fixture(self):
        self.assertTrue(True)
PY
cat > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/p2p_contracts/tests/test_cli_bootstrap.py" <<'PY'
import unittest
class P2PBootstrapFixtureTest(unittest.TestCase):
    def test_fixture(self):
        self.assertTrue(True)
PY
cat > "$TEST_FIXTURES/release/Node-Core-OS-test/applications/p2p_contracts/tests/test_cli_local_manifest.py" <<'PY'
import unittest
class P2PLocalManifestFixtureTest(unittest.TestCase):
    def test_fixture(self):
        self.assertTrue(True)
PY

printf 'P2P documentation fixture\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/docs/P2P-CONTRACTS-TECHNICAL-AUDIT.md"
printf 'name: suspended P2P fixture\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/.github/workflows/three-independent-ubuntu-p2p-contracts.yml"
printf 'name: suspended P2P E2E fixture\n' > "$TEST_FIXTURES/release/Node-Core-OS-test/.github/workflows/three-independent-ubuntu-p2p-e2e.yml"

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

cat > "$TEMP_ROOT/fake-bin/pkg" <<'FAKE_PKG'
#!/usr/bin/env bash
exit 0
FAKE_PKG
chmod +x "$TEMP_ROOT/fake-bin/pkg"

REAL_UNAME="$(command -v uname)"
cat > "$TEMP_ROOT/fake-bin/uname" <<'FAKE_UNAME'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" ]]; then
  printf 'aarch64\\n'
else
  exec "$REAL_UNAME" "$@"
fi
FAKE_UNAME
chmod +x "$TEMP_ROOT/fake-bin/uname"
export REAL_UNAME

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
  */commits/main|*/commits\?sha=main\&per_page=1) cp "$TEST_FIXTURES/latest-commit.json" "$output" ;;
  */archive/5555555555555555555555555555555555555555.tar.gz) cp "$TEST_FIXTURES/5555555555555555555555555555555555555555.tar.gz" "$output" ;;
  *) printf 'unexpected URL in Termux updater test: %s\n' "$url" >&2; exit 3 ;;
esac
FAKE_CURL
chmod +x "$TEMP_ROOT/fake-bin/curl"
export PATH="$TEMP_ROOT/fake-bin:$PREFIX/bin:$PATH"

printf "y\n" | bash "$NODE_CORE_DATA_DIR/app/installer/update.sh"

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
grep -qx '1.2.6' "$NODE_CORE_DATA_DIR/app/VERSION"
assert_identity_and_data_preserved
PYTHONPATH="$REPOSITORY_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  python3 "$TEST_FIXTURES/persistence-check.py" capture \
  "$NODE_CORE_DATA_DIR" "$TEST_FIXTURES/persistence-after-update.json"
PYTHONPATH="$REPOSITORY_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  python3 "$TEST_FIXTURES/persistence-check.py" compare \
  "$TEST_FIXTURES/persistence-before.json" "$TEST_FIXTURES/persistence-after-update.json"
test ! -e "$NODE_CORE_DATA_DIR/app/applications/hashpaper"
test ! -e "$NODE_CORE_DATA_DIR/app/applications/p2p_contracts"
test ! -e "$NODE_CORE_DATA_DIR/app/docs/P2P-CONTRACTS-TECHNICAL-AUDIT.md"
test ! -e "$NODE_CORE_DATA_DIR/app/.github/workflows/three-independent-ubuntu-p2p-contracts.yml"
test ! -e "$NODE_CORE_DATA_DIR/app/.github/workflows/three-independent-ubuntu-p2p-e2e.yml"
test -x "$NODE_CORE_DATA_DIR/bin/node-core"
test -x "$NODE_CORE_DATA_DIR/bin/node-core-update"
grep -q '^include-system-site-packages = true$' "$NODE_CORE_DATA_DIR/runtime/node-core-venv/pyvenv.cfg"

# An interrupted cleanup can leave marker files after the app backup has gone.
# The updater must validate the installed app, archive the markers, and continue.
printf 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n' > "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-backup"
printf 'present\n' > "$NODE_CORE_DATA_DIR/runtime/update/commit-marker-state"
test ! -e "$NODE_CORE_DATA_DIR/runtime/update/app-backup"
bash "$NODE_CORE_DATA_DIR/app/installer/update.sh" > "$TEMP_ROOT/stale-cleanup-recovery.log" 2>&1
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
assert_identity_and_data_preserved
PYTHONPATH="$REPOSITORY_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  python3 "$TEST_FIXTURES/persistence-check.py" capture \
  "$NODE_CORE_DATA_DIR" "$TEST_FIXTURES/persistence-after-recovery.json"
PYTHONPATH="$REPOSITORY_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  python3 "$TEST_FIXTURES/persistence-check.py" compare \
  "$TEST_FIXTURES/persistence-before.json" "$TEST_FIXTURES/persistence-after-recovery.json"

printf 'Termux updater stale-cleanup recovery test passed.\n'

printf 'Termux updater real-update and data-preservation tests passed.\n'
