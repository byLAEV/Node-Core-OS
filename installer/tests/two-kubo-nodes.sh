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
API_A="/ip4/127.0.0.1/tcp/5101"
API_B="/ip4/127.0.0.1/tcp/5102"
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

download_file() {
    local asset="$1"
    local destination="$2"
    local github_url="https://github.com/ipfs/kubo/releases/download/v${KUBO_VERSION}/$asset"
    local dist_url="https://dist.ipfs.tech/kubo/v${KUBO_VERSION}/$asset"

    echo "Downloading $asset from the official GitHub release..."
    if curl --fail --location --silent --show-error --retry 2 \
        --connect-timeout 15 --max-time 180 "$github_url" -o "$destination"; then
        return 0
    fi

    echo "GitHub release download failed; trying the official dist.ipfs.tech mirror..."
    if curl --fail --location --silent --show-error --retry 2 \
        --connect-timeout 15 --max-time 180 "$dist_url" -o "$destination"; then
        return 0
    fi

    return 1
}

node_a() {
    "$IPFS" --api="$API_A" "$@"
}

node_b() {
    "$IPFS" --api="$API_B" "$@"
}

mkdir -p "$DOWNLOAD_DIR" "$REPO_A" "$REPO_B"

ARCHIVE="kubo_v${KUBO_VERSION}_linux-amd64.tar.gz"
CHECKSUM="${ARCHIVE}.sha512"

echo "Preparing official Kubo release: $KUBO_VERSION"
download_file "$ARCHIVE" "$DOWNLOAD_DIR/$ARCHIVE" || fail "Could not download Kubo archive from either official source."
download_file "$CHECKSUM" "$DOWNLOAD_DIR/$CHECKSUM" || fail "Could not download the official Kubo SHA-512 checksum."

(
    cd "$DOWNLOAD_DIR"
    sha512sum --check "$CHECKSUM"
) || fail "Kubo archive checksum verification failed."

tar -xzf "$DOWNLOAD_DIR/$ARCHIVE" -C "$DOWNLOAD_DIR"
IPFS="$DOWNLOAD_DIR/kubo/ipfs"
test -x "$IPFS" || fail "Kubo executable was not found in the official archive."
"$IPFS" version

echo "Initializing two independent Kubo repositories"
IPFS_PATH="$REPO_A" "$IPFS" init --profile=test
IPFS_PATH="$REPO_B" "$IPFS" init --profile=test

# Both nodes run on the same GitHub Actions runner, but use independent repositories
# and distinct API, gateway, and swarm ports.
IPFS_PATH="$REPO_A" "$IPFS" config Addresses.API "$API_A"
IPFS_PATH="$REPO_A" "$IPFS" config Addresses.Gateway /ip4/127.0.0.1/tcp/8181
IPFS_PATH="$REPO_A" "$IPFS" config Addresses.Swarm '["/ip4/127.0.0.1/tcp/4101"]' --json

IPFS_PATH="$REPO_B" "$IPFS" config Addresses.API "$API_B"
IPFS_PATH="$REPO_B" "$IPFS" config Addresses.Gateway /ip4/127.0.0.1/tcp/8182
IPFS_PATH="$REPO_B" "$IPFS" config Addresses.Swarm '["/ip4/127.0.0.1/tcp/4102"]' --json

echo "Starting Kubo daemon A"
IPFS_PATH="$REPO_A" "$IPFS" daemon >"$LOG_A" 2>&1 &
PID_A=$!

echo "Starting Kubo daemon B"
IPFS_PATH="$REPO_B" "$IPFS" daemon >"$LOG_B" 2>&1 &
PID_B=$!

wait_for_api() {
    local label="$1"
    shift
    local attempts=0
    until "$@" >/dev/null 2>&1; do
        attempts=$((attempts + 1))
        if [ "$attempts" -ge 60 ]; then
            fail "$label API did not become ready within 60 seconds."
        fi
        sleep 1
    done
    echo "$label API is ready."
}

wait_for_api "Node A" node_a id
wait_for_api "Node B" node_b id

PEER_A="$(node_a id --format='<id>')"
PEER_B="$(node_b id --format='<id>')"

test -n "$PEER_A" || fail "Node A did not return a peer ID."
test -n "$PEER_B" || fail "Node B did not return a peer ID."
test "$PEER_A" != "$PEER_B" || fail "The two repositories unexpectedly share the same peer ID."

echo "Node A peer ID: $PEER_A"
echo "Node B peer ID: $PEER_B"
echo "Connecting Node A to Node B"
ADDRESS_B="/ip4/127.0.0.1/tcp/4102/p2p/$PEER_B"
node_a swarm connect "$ADDRESS_B"

echo "Waiting for Node A to report Node B as a connected peer"
attempts=0
until node_a swarm peers | grep -F "$PEER_B" >/dev/null; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 30 ]; then
        fail "Node A did not report Node B as connected."
    fi
    sleep 1
done

echo "Waiting for Node B to report Node A as a connected peer"
attempts=0
until node_b swarm peers | grep -F "$PEER_A" >/dev/null; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 30 ]; then
        fail "Node B did not report Node A as connected."
    fi
    sleep 1
done

echo "Testing peer reachability with Kubo ping"
node_a ping -n 1 "$PEER_B"

echo "Verifying both nodes list the other peer"
node_a swarm peers | tee "$WORK_DIR/node-a-peers.txt"
node_b swarm peers | tee "$WORK_DIR/node-b-peers.txt"
grep -F "$PEER_B" "$WORK_DIR/node-a-peers.txt" >/dev/null
grep -F "$PEER_A" "$WORK_DIR/node-b-peers.txt" >/dev/null

echo "PASS: two independent Kubo nodes have different identities, connected to each other, and completed a peer ping."
