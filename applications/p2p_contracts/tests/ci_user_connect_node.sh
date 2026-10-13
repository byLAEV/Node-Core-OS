#!/usr/bin/env bash
# Connect an installed Kubo daemon to the other two independent test nodes.
set -euo pipefail
node_name="${1:?node name required}"
peer_one_host="${2:?peer one IPv4 host required}"
peer_one_id="${3:?peer one ID required}"
peer_two_host="${4:?peer two IPv4 host required}"
peer_two_id="${5:?peer two ID required}"

case "$node_name" in node-a|node-b|node-c) ;; *) echo "Invalid node name" >&2; exit 2 ;; esac
test "$(id -u)" -ne 0 || { echo "ERROR: runner must not be root" >&2; exit 1; }
: "${GITHUB_RUN_ID:?GitHub Actions run ID is required}"
export NODE_CORE_DATA_DIR="$HOME/.node-core-p2p-e2e/$GITHUB_RUN_ID/$node_name"
export IPFS_PATH="$NODE_CORE_DATA_DIR/ipfs"
ipfs="$NODE_CORE_DATA_DIR/bin/ipfs"
test -x "$ipfs"
test -n "$peer_one_host"
test -n "$peer_two_host"
test -n "$peer_one_id"
test -n "$peer_two_id"

local_id="$("$ipfs" id --format='<id>')"
echo "LOCAL_NODE=$node_name UID=$(id -u) PEER_ID=$local_id"
"$ipfs" swarm connect "/ip4/$peer_one_host/tcp/4001/p2p/$peer_one_id"
"$ipfs" swarm connect "/ip4/$peer_two_host/tcp/4001/p2p/$peer_two_id"

for attempt in $(seq 1 60); do
  peers="$("$ipfs" swarm peers)"
  count="$(printf '%s\n' "$peers" | grep -c '/p2p/' || true)"
  if [ "$count" -ge 2 ]; then
    printf 'THREE_NODE_SWARM_OK node=%s peer_id=%s connected_peers=%s\n' "$node_name" "$local_id" "$count"
    printf '%s\n' "$peers"
    exit 0
  fi
  sleep 1
done

echo "ERROR: node $node_name did not establish two direct peer connections." >&2
"$ipfs" swarm peers >&2
if [ -f "$NODE_CORE_DATA_DIR/logs/kubo.log" ]; then
  tail -n 100 "$NODE_CORE_DATA_DIR/logs/kubo.log" >&2
fi
exit 1
