#!/usr/bin/env bash
set -euo pipefail

# Real two-node Kubo integration test for GitHub Actions.
# Each node uses a separate repository, API port, gateway port, and swarm port.

KUBO_VERSION="${KUBO_VERSION:-0.42.0}"
WORK_DIR="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/node-core-two-node-test-$$"
DOWNLOAD_DIR="$WORK_DIR/download"
REPO_A="$WORK_DIR/node-a"
REPO_B="$WORK_DIR/node-b"
LOG_A="$WORK_DIR/node-a-daemon.log"
LOG_B="$WORK_DIR/node-b-daemon.log"
PID_A=""
PID_B=""

cleanup() {
    if [ -n "$PID_A" ]; then kill "$PID_A" 2>/dev/null || true; fi
    if [ -n "$PID_B" ]; then kill "$PID_B" 2>/dev/null || true; fi
    if [ -n "$PID_A" ]; then wait "$PID_A" 2>/dev/null || true; fi
    if [ -n "$PID_B" ]; then wait "$PID_B" 2>/dev/null || true; fi
    if [ "${KEEP_NODE_TEST_FILES:-0}" != "1" ]; then
        rm -rf "$WORK_DIR"
    else
        echo "Keeping test files at $WORK_DIR"
    fi
}
trap cleanup EXIT

fail() {
    echo "ERROR: $*" >&2
    echo "===== Node A daemon log =====" >&2
    if [ -f "$LOG_A" ]; then cat "$LOG_A" >&2; fi
    echo "===== Node B daemon log =====" >&2
    if [ -f "$LOG_B" ]; then cat "$LOG_B" >&2; fi
    exit 1
}

mkdir -p "$DOWNLOAD_DIR" "$REPO_A" "$REPO_B"

ARCHIVE="kubo_v${KUBO_VERSION}_linux-amd64.tar.gz"
BASE_URL="https://dist.ipfs.tech/kubo/v${KUBO_VERSION}"
echo "Downloading official Kubo release: $KUBO_VERSION"
curl --fail --location --retry 3 --connect-timeout 20 \
    "$BASE_URL/$ARCHIVE" -o "$DOWNLOAD_DIR/$ARCHIVE"
curl --fail --location --retry 3 --connect-timeout 20 \
    "$BASE_URL/$ARCHIVE.sha512" -o "$DOWNLOAD_DIR/$ARCHIVE.sha512"
(
    cd "$DOWNLOAD_DIR"
    sha512sum --check "$ARCHIVE.sha512"
)
tar -xzf "$DOWNLOAD_DIR/$ARCHIVE" -C "$DOWNLOAD_DIR"
IPFS="$DOWNLOAD_DIR/kubo/ipfs"
test -x "$IPFS" || fail "Kubo executable was not found in the official archive."
"$IPFS" version

echo "Initializing two independent Kubo repositories"
IPFS_PATH="$REPO_A" "$IPFS" init --profile=test
IPFS_PATH="$REPO_B" "$IPFS" init --profile=test

# Use loopback addresses because both test nodes run on the same GitHub Actions runner.
# The separate ports and repository directories represent independent node identities.
IPFS_PATH="$REPO_A" "$IPFS" config Addresses.API /ip4/127.0.0.1/tcp/5101
IPFS_PATH="$REPO_A" "$IPFS" config Addresses.Gateway /ip4/127.0.0.1/tcp/8181
IPFS_PATH="$REPO_A" "$IPFS" config Addresses.Swarm '["/ip4/127.0.0.1/tcp/4101"]' --json

IPFS_PATH="$REPO_B" "$IPFS" config Addresses.API /ip4/127.0.0.1/tcp/5102
IPFS_PATH="$REPO_B" "$IPFS" config Addresses.Gateway /ip4/127.0.0.1/tcp/8182
IPFS_PATH="$REPO_B" "$IPFS" config Addresses.Swarm '["/ip4/127.0.0.1/tcp/4102"]' --json

echo "Starting Kubo daemon A"
IPFS_PATH="$REPO_A" "$IPFS" daemon >"$LOG_A" 2>&1 &
PID_A=$!

echo "Starting Kubo daemon B"
IPFS_PATH="$REPO_B" "$IPFS" daemon >"$LOG_B" 2>&1 &
PID_B=$!

wait_for_api() {
    local repo="$1"
    local label="$2"
    local attempts=0
    until IPFS_PATH="$repo" "$IPFS" id >/dev/null 2>&1; do
        attempts=$((attempts + 1))
        if [ "$attempts" -ge 60 ]; then
            fail "$label API did not become ready within 60 seconds."
        fi
        sleep 1
    done
    echo "$label API is ready."
}

wait_for_api "$REPO_A" "Node A"
wait_for_api "$REPO_B" "Node B"

PEER_A="$(IPFS_PATH="$REPO_A" "$IPFS" id --format='<id>')"
PEER_B="$(IPFS_PATH="$REPO_B" "$IPFS" id --format='<id>')"

test -n "$PEER_A" || fail "Node A did not return a peer ID."
test -n "$PEER_B" || fail "Node B did not return a peer ID."
test "$PEER_A" != "$PEER_B" || fail "The two repositories unexpectedly share the same peer ID."

echo "Node A peer ID: $PEER_A"
echo "Node B peer ID: $PEER_B"
echo "Connecting Node A to Node B"
ADDRESS_B="/ip4/127.0.0.1/tcp/4102/p2p/$PEER_B"
IPFS_PATH="$REPO_A" "$IPFS" swarm connect "$ADDRESS_B"

echo "Waiting for Node A to report Node B as a connected peer"
attempts=0
until IPFS_PATH="$REPO_A" "$IPFS" swarm peers | grep -F "$PEER_B" >/dev/null; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 30 ]; then
        fail "Node A did not report Node B as connected."
    fi
    sleep 1
done

echo "Waiting for Node B to report Node A as a connected peer"
attempts=0
until IPFS_PATH="$REPO_B" "$IPFS" swarm peers | grep -F "$PEER_A" >/dev/null; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 30 ]; then
        fail "Node B did not report Node A as connected."
    fi
    sleep 1
done

echo "Testing peer reachability with Kubo ping"
IPFS_PATH="$REPO_A" "$IPFS" ping -n 1 "$PEER_B"

echo "Verifying both nodes list the other peer"
IPFS_PATH="$REPO_A" "$IPFS" swarm peers | tee "$WORK_DIR/node-a-peers.txt"
IPFS_PATH="$REPO_B" "$IPFS" swarm peers | tee "$WORK_DIR/node-b-peers.txt"
grep -F "$PEER_B" "$WORK_DIR/node-a-peers.txt" >/dev/null
grep -F "$PEER_A" "$WORK_DIR/node-b-peers.txt" >/dev/null

echo "PASS: two independent Kubo nodes have different identities, connected to each other, and completed a peer ping."
