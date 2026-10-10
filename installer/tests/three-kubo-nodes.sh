#!/usr/bin/env bash
set -euo pipefail
# Three independent Kubo repositories, full-mesh connectivity, and content transfer.
KUBO_VERSION="${KUBO_VERSION:-0.43.1}"
WORK_DIR="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/node-core-three-node-test-$$"
DOWNLOAD_DIR="$WORK_DIR/download"
REPOS=("$WORK_DIR/node-a" "$WORK_DIR/node-b" "$WORK_DIR/node-c")
LOGS=("$WORK_DIR/node-a.log" "$WORK_DIR/node-b.log" "$WORK_DIR/node-c.log")
APIS=("/ip4/127.0.0.1/tcp/5101" "/ip4/127.0.0.1/tcp/5102" "/ip4/127.0.0.1/tcp/5103")
SWARMS=("/ip4/127.0.0.1/tcp/4101" "/ip4/127.0.0.1/tcp/4102" "/ip4/127.0.0.1/tcp/4103")
GATEWAYS=("/ip4/127.0.0.1/tcp/8181" "/ip4/127.0.0.1/tcp/8182" "/ip4/127.0.0.1/tcp/8183")
PIDS=()
IPFS=""
cleanup() {
    for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
    for pid in "${PIDS[@]}"; do wait "$pid" 2>/dev/null || true; done
    if [ "${KEEP_NODE_TEST_FILES:-0}" = "1" ]; then echo "Keeping test files at $WORK_DIR"; else rm -rf "$WORK_DIR"; fi
}
trap cleanup EXIT
fail() {
    echo "ERROR: $*" >&2
    for log in "${LOGS[@]}"; do echo "===== $log =====" >&2; [ ! -f "$log" ] || cat "$log" >&2; done
    exit 1
}
mkdir -p "$DOWNLOAD_DIR" "${REPOS[@]}"
ARCHIVE="kubo_v${KUBO_VERSION}_linux-amd64.tar.gz"
CHECKSUM="${ARCHIVE}.sha512"
BASE="https://github.com/ipfs/kubo/releases/download/v${KUBO_VERSION}"
curl --fail --location --silent --show-error --retry 2 --connect-timeout 15 --max-time 180 "$BASE/$ARCHIVE" -o "$DOWNLOAD_DIR/$ARCHIVE" || fail "Could not download official Kubo archive."
curl --fail --location --silent --show-error --retry 2 --connect-timeout 15 --max-time 180 "$BASE/$CHECKSUM" -o "$DOWNLOAD_DIR/$CHECKSUM" || fail "Could not download official Kubo checksum."
(cd "$DOWNLOAD_DIR" && sha512sum --check "$CHECKSUM") || fail "Kubo SHA-512 verification failed."
tar -xzf "$DOWNLOAD_DIR/$ARCHIVE" -C "$DOWNLOAD_DIR"
IPFS="$DOWNLOAD_DIR/kubo/ipfs"
test -x "$IPFS" || fail "Kubo executable missing."
"$IPFS" version
for i in 0 1 2; do
    IPFS_PATH="${REPOS[$i]}" "$IPFS" init --profile=test
    IPFS_PATH="${REPOS[$i]}" "$IPFS" config Addresses.API "${APIS[$i]}"
    IPFS_PATH="${REPOS[$i]}" "$IPFS" config Addresses.Gateway "${GATEWAYS[$i]}"
        IPFS_PATH="${REPOS[$i]}" "$IPFS" config Addresses.Swarm "[\"${SWARMS[$i]}\"]" --json
done
node() { local index="$1"; shift; "$IPFS" --api="${APIS[$index]}" "$@"; }
for i in 0 1 2; do IPFS_PATH="${REPOS[$i]}" "$IPFS" daemon >"${LOGS[$i]}" 2>&1 & PIDS+=("$!"); done
for i in 0 1 2; do
    ready=0
    for attempt in $(seq 1 60); do if node "$i" id >/dev/null 2>&1; then ready=1; break; fi; sleep 1; done
    [ "$ready" -eq 1 ] || fail "Node $i API not ready after 60 seconds."
done
PEERS=()
for i in 0 1 2; do PEERS[$i]="$(node "$i" id --format='<id>')"; test -n "${PEERS[$i]}" || fail "Node $i has no peer ID."; done
[ "${PEERS[0]}" != "${PEERS[1]}" ] || fail "Nodes 0 and 1 share an identity."
[ "${PEERS[0]}" != "${PEERS[2]}" ] || fail "Nodes 0 and 2 share an identity."
[ "${PEERS[1]}" != "${PEERS[2]}" ] || fail "Nodes 1 and 2 share an identity."
# Explicitly connect every node to both other nodes.
for i in 0 1 2; do
    for j in 0 1 2; do
        [ "$i" -eq "$j" ] && continue
        port=$((4101 + j))
        node "$i" swarm connect "/ip4/127.0.0.1/tcp/$port/p2p/${PEERS[$j]}"
    done
done
for i in 0 1 2; do
    for j in 0 1 2; do
        [ "$i" -eq "$j" ] && continue
        connected=0
        for attempt in $(seq 1 30); do if node "$i" swarm peers | grep -F "${PEERS[$j]}" >/dev/null; then connected=1; break; fi; sleep 1; done
        [ "$connected" -eq 1 ] || fail "Node $i does not see node $j as connected."
    done
done
node 0 ping -n 1 "${PEERS[1]}"
node 0 ping -n 1 "${PEERS[2]}"
node 1 ping -n 1 "${PEERS[2]}"
# Each node publishes unique content; both other nodes retrieve it by CID.
for publisher in 0 1 2; do
    source="$WORK_DIR/source-node-$publisher.txt"
    printf 'Node Core OS multi-node transfer test: publisher %s\n' "$publisher" > "$source"
    cid="$(node "$publisher" add --quiet "$source")"
    test -n "$cid" || fail "Node $publisher did not return a CID."
    for receiver in 0 1 2; do
        [ "$publisher" -eq "$receiver" ] && continue
        destination="$WORK_DIR/received-$publisher-by-$receiver.txt"
        node "$receiver" cat "$cid" > "$destination" || fail "Node $receiver could not retrieve content from node $publisher."
        cmp -s "$source" "$destination" || fail "Content mismatch from node $publisher to node $receiver."
        source_sha="$(sha256sum "$source" | awk '{print $1}')"
        received_sha="$(sha256sum "$destination" | awk '{print $1}')"
        [ "$source_sha" = "$received_sha" ] || fail "SHA-256 mismatch from node $publisher to node $receiver."
        echo "PASS: node $publisher -> node $receiver | CID=$cid | SHA-256=$source_sha"
    done
done
echo "PASS: three independent Kubo nodes, distinct identities, full-mesh connectivity, all pairwise pings, and six verified content transfers."
