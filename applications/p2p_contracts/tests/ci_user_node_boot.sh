#!/usr/bin/env bash
# First-boot acceptance helper. Must run as the ordinary self-hosted runner user.
set -euo pipefail

node_name="\${1:?node name required: node-a, node-b, or node-c}"
full_name="\${2:?synthetic full name required}"
alias_name="\${3:?synthetic alias required}"
document_number="\${4:?synthetic document number required}"

case "$node_name" in
  node-a|node-b|node-c) ;;
  *) echo "ERROR: unsupported node name: $node_name" >&2; exit 2 ;;
esac

test "$(id -u)" -ne 0 || { echo "ERROR: this workflow must never run as root" >&2; exit 1; }
if ! grep -q '^ID=ubuntu$' /etc/os-release || ! grep -q '^VERSION_ID="24.04"$' /etc/os-release; then
  echo "ERROR: each independent runner must be Ubuntu 24.04." >&2
  cat /etc/os-release >&2
  exit 1
fi
machine_fingerprint="$(sha256sum /etc/machine-id | awk '{print $1}')"
test -n "$machine_fingerprint"
printf 'UBUNTU_RUNNER_OK node=%s version=24.04 machine_fingerprint=%s\n' "$node_name" "$machine_fingerprint"
export NODE_CORE_MACHINE_FINGERPRINT="$machine_fingerprint"

for command in bash python3 curl tar sha512sum timeout; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "ERROR: required user-level command is missing: $command" >&2
    exit 1
  }
done
: "\${GITHUB_RUN_ID:?GitHub Actions run ID is required}"
: "\${GITHUB_OUTPUT:?GitHub Actions output file is required}"
: "\${RUNNER_TEMP:?GitHub Actions runner temp directory is required}"

export NODE_CORE_DATA_DIR="$HOME/.node-core-p2p-e2e/$GITHUB_RUN_ID/$node_name"
export IPFS_PATH="$NODE_CORE_DATA_DIR/ipfs"
mkdir -p "$HOME/.node-core-p2p-e2e/$GITHUB_RUN_ID"

echo "RUN_USER=$USER UID=$(id -u) NODE=$node_name DATA_DIR=$NODE_CORE_DATA_DIR"
bash installer/install.sh
test -x "$NODE_CORE_DATA_DIR/bin/node-core"
test -x "$NODE_CORE_DATA_DIR/bin/ipfs"
test -f "$NODE_CORE_DATA_DIR/app/applications/p2p_contracts/main.py"

# Kubo must be available before the first Node Core OS menu is opened.
peer_id=""
for attempt in $(seq 1 60); do
  if peer_id="$("$NODE_CORE_DATA_DIR/bin/ipfs" id --format='<id>')" && [ -n "$peer_id" ]; then
    break
  fi
  sleep 1
done
test -n "$peer_id"
printf 'KUBO_ONLINE_BEFORE_FIRST_BOOT node=%s peer_id=%s uid=%s\n' "$node_name" "$peer_id" "$(id -u)"

# First-boot menu -> Node Core BIOS -> Identity Profile (option 10).
# Synthetic QA data only; never use real identity documents in CI.
printf '1\n10\n1\n%s\n%s\nCosta Rican\nCosta Rica\nSynthetic QA identity document\n%s\n1990-01-01\n170\nSynthetic\n\n2\n\n0\n0\n0\n' \
  "$full_name" "$alias_name" "$document_number" |
  timeout 90 "$NODE_CORE_DATA_DIR/bin/node-core" > "$RUNNER_TEMP/$node_name-first-boot.log" 2>&1
cat "$RUNNER_TEMP/$node_name-first-boot.log"

grep -q 'Identity profile saved locally as declared data' "$RUNNER_TEMP/$node_name-first-boot.log"
grep -q 'Identity profile associated with the current node' "$RUNNER_TEMP/$node_name-first-boot.log"
grep -q "Name: $full_name" "$RUNNER_TEMP/$node_name-first-boot.log"
grep -q "Document number: $document_number" "$RUNNER_TEMP/$node_name-first-boot.log"

profile="$NODE_CORE_DATA_DIR/identity/profile.json"
test -f "$profile"
python3 - "$profile" "$NODE_CORE_DATA_DIR/bin/ipfs" "$IPFS_PATH" "$full_name" "$document_number" <<'PY'
import json, os, subprocess, sys
from pathlib import Path

profile_path = Path(sys.argv[1])
profile = json.loads(profile_path.read_text(encoding="utf-8"))
env = {**os.environ, "IPFS_PATH": sys.argv[3]}
peer = json.loads(subprocess.run(
    [sys.argv[2], "id"], env=env, check=True, capture_output=True, text=True
).stdout)["ID"]
assert profile.get("identity_status") == "declared", profile
assert profile.get("full_name") == sys.argv[4], profile
assert profile.get("document_number") == sys.argv[5], profile
assert profile.get("node_id") == peer, (profile.get("node_id"), peer)
assert profile_path.stat().st_mode & 0o077 == 0, oct(profile_path.stat().st_mode & 0o777)
print(f"IDENTITY_OK identity_id={profile['identity_id']} peer_id={peer}")
with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
    output.write(f"peer_id={peer}\n")
    output.write(f"identity_id={profile['identity_id']}\n")
    output.write(f"machine_fingerprint={os.environ['NODE_CORE_MACHINE_FINGERPRINT']}\n")
PY

# Launch P2P Contracts through the real Node Core OS Applications menu and
# explicitly accept use of the already configured local identity.
printf '4\n2\ny\n0\n0\n0\n' |
  timeout 60 "$NODE_CORE_DATA_DIR/bin/node-core" > "$RUNNER_TEMP/$node_name-p2p-menu.log" 2>&1
cat "$RUNNER_TEMP/$node_name-p2p-menu.log"
grep -q 'NODE CORE OS P2P CONTRACTS' "$RUNNER_TEMP/$node_name-p2p-menu.log"
grep -q "$full_name" "$RUNNER_TEMP/$node_name-p2p-menu.log"
! grep -q 'Identity consent was not granted' "$RUNNER_TEMP/$node_name-p2p-menu.log"

echo "NODE_FIRST_BOOT_AND_P2P_MENU_OK node=$node_name peer_id=$peer_id"
