# Real Linux 20–100 node full-mesh synchronization campaign

This campaign is designed to be proven first on operator-controlled Linux
terminals and then reproduced on GitHub Actions. Both modes execute the same
Node Core OS participant program: `ci/linux/real_multi_node_mesh.py`.

## Phase 1 — manual Linux terminal deployment

Use separate Linux machines or VMs. Each machine must be reachable over the
same private network. Tailscale is the documented overlay option; a private
LAN/VPN with equivalent reachability also works if firewall rules allow TCP
8765 and 46000 between every participant.

### 1. Install prerequisites on every machine

Run as the normal login user, never with `sudo` for Node Core OS:

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates python3 python3-venv python3-pip
```

Install and authenticate Tailscale according to its official Linux
instructions. Join every machine to the same tailnet. Confirm:

```bash
tailscale status
tailscale ip -4
```

Configure the tailnet ACL to allow TCP 8765 and 46000 among the participating
machines. The rendezvous server is hosted by node 0 on port 8765. Every node
hosts its native Node Core OS P2P listener on port 46000.

### 2. Clone and install Node Core OS on every machine

```bash
git clone https://github.com/byLAEV/Node-Core-OS.git
cd Node-Core-OS
bash installer/install.sh
```

The installer must be run without `sudo`. It creates the user-level
installation at `$HOME/.node-core`, initializes a persistent Ed25519 node
identity, prepares the Python virtual environment and installs Kubo.

### 3. Assign one index per machine

For a 3-node smoke test, use indices 0, 1 and 2 and set `NODE_COUNT=3`.
For the full campaign, use indices 0 through 99 and set `NODE_COUNT=100`.
Every participant must use the same numeric `MESH_RUN_ID`. Example:

```bash
export MESH_RUN_ID=2026110701
export NODE_COUNT=3
```

On node 0:

```bash
export NODE_INDEX=0
bash ci/linux/run_manual_mesh.sh
```

Read node 0's Tailscale IPv4 address from `tailscale ip -4`. On each other
machine, set its unique index and the coordinator address, then run the same
script:

```bash
export NODE_INDEX=1
export MESH_COORDINATOR_IP=100.x.y.z
bash ci/linux/run_manual_mesh.sh
```

Use `NODE_INDEX=2` on the third machine, and so on. Start node 0 first, then
start all remaining nodes within the same campaign window. Keep every terminal
running until the participant prints `NODE_FULL_MESH_PASS`. Do not reuse a
node index or campaign ID for a different test run.

The script validates the user-level installation, Python environment,
Tailscale connection and participant arguments. It does not create trust by
blindly accepting unknown peers: the test roster exchanges public certificates
and RSA public keys, and Node Core OS uses its authenticated P2P transport.

### 4. Verify the results on every machine

A successful participant must report:
- a unique persistent node ID;
- a complete roster and unanimous manifest verification;
- exactly `NODE_COUNT - 1` outgoing delivery receipts;
- exactly `NODE_COUNT - 1` incoming persistent replicas;
- matching network-state and convergence SHA-256 hashes;
- `NODE_FULL_MESH_PASS`.

Evidence JSON files are written under
`$NODE_CORE_DATA_DIR/logs/node-core-mesh-evidence/`. On each machine inspect:

```bash
find "$HOME/.node-core/logs/node-core-mesh-evidence" -maxdepth 1 -type f -name 'node-*.json' -print
```

Start with 3 nodes, then 5 or 10, then 20. Move to 50 and 100 only after the
previous size has completed successfully on independent Linux machines.

## Phase 2 — reproduce the same test on GitHub Actions

The workflow `.github/workflows/real-linux-100-node-campaign.yml` provisions
one GitHub-hosted Ubuntu 24.04 runner VM per participant. Each matrix job
checks out the repository, joins the private Tailscale network, installs
Node Core OS as the runner user, and runs the same participant program with a
unique index and shared campaign ID. It uploads one evidence artifact per
node.

Configure repository Actions secrets `TS_OAUTH_CLIENT_ID` and
`TS_OAUTH_SECRET` for the Tailscale OAuth client. The client must be able to
create ephemeral auth keys with tag `tag:node-core-ci`. The tailnet ACL must
allow tagged peers to reach TCP 8765 and 46000. Never commit these credentials.

To launch the 100-node campaign, open Actions, select **Node Core OS — 100
independent Linux nodes**, choose **Run workflow**, and set
`confirm_100_nodes=true`. A push to the feature branch only runs the campaign
when its commit message explicitly contains `[run-100-node-campaign]`.

The 100-node campaign requires 100 simultaneously available runner slots.
`max-parallel: 100` is a cap, not a quota increase. If the account's
concurrency limit is lower, the full-roster barrier cannot complete. In that
case use an approved higher concurrency allowance or a self-hosted fleet of
100 separate Linux VMs.

## Network policy for Tailscale

Merge the following tag owner and ACL fragment into the existing tailnet
policy. Do not replace unrelated policy rules:

```json
{
  "tagOwners": {
    "tag:node-core-ci": ["autogroup:admin"]
  },
  "acls": [
    {
      "action": "accept",
      "src": ["tag:node-core-ci"],
      "dst": ["tag:node-core-ci:8765,46000"]
    }
  ]
}
```

## What the test proves

1. Each runner is a separate Ubuntu 24.04 Linux VM and runs as a non-root user.
2. Each VM installs Node Core OS and creates its own unique node identity.
3. All nodes register public identity metadata and sign one common presence
   manifest. Every participant verifies the unanimous signatures.
4. Each node starts the native Node Core OS P2P service with trusted peer
   certificates and RSA public keys.
5. Each node sends one identical campaign record to every other node using
   the existing `NodeRecordReplicator` and secure P2P transport.
6. Each receiver validates the authenticated sender, recipient, record owner,
   record ID and schema, then persists the received record locally.
7. Every node waits for and verifies 99 persistent replicas (for a 100-node
   campaign), plus its own contribution.
8. Every participant calculates the same canonical network-state hash and
   convergence hash. Each runner uploads an evidence JSON file.

A 100-node full directed mesh produces 100 × 99 = **9,900 directed deliveries**.
The rendezvous service distributes only public metadata and signatures; it is
not a message relay. The actual replicated records are sent through the
Node Core OS P2P service over the private Tailscale network.

## Evidence and honest limitations

Download the `node-core-real-linux-node-N` artifacts from the completed run.
Each node report contains its runner hostname, OS, UID, node ID, manifest
signature count, state hash, convergence hash, 99 outgoing receipts, 99
incoming persistent replicas and sampled Tailscale route diagnostics.

Tailscale may use direct peer paths or DERP relays. The evidence records route
diagnostics rather than assuming every path is physically direct. The GitHub
runners are separate VMs but share a cloud provider; they are not 100
independent physical operators or geographically diverse autonomous systems.

Unanimous identity signatures and identical replicated records demonstrate
membership recognition and data convergence. They do **not** constitute
Byzantine fault-tolerant consensus, conflict-free concurrent writes, or
production-grade distributed consensus. Those require a separate protocol
and adversarial fault tests.
