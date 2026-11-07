# Real Linux 20–100 node full-mesh synchronization campaign

This opt-in GitHub Actions campaign launches one independent GitHub-hosted
Ubuntu 24.04 runner VM per node. Every VM installs Node Core OS as its normal
runner user and receives its own persistent runner-local data directory,
Ed25519 identity, TLS certificate and RSA messaging identity.

## Required Tailscale setup

Create a Tailscale OAuth client with permission to create ephemeral auth keys
and apply the tag `tag:node-core-ci`. Add GitHub Actions repository secrets:

- `TS_OAUTH_CLIENT_ID`
- `TS_OAUTH_SECRET`

Merge the following tag owner and ACL fragment into the existing tailnet
policy. Do not replace unrelated policy rules. This allows the temporary
rendezvous service and direct P2P transport between tagged nodes:

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

Check the current Tailscale action documentation and OAuth scope requirements
when configuring the client. Do not commit OAuth credentials or auth keys.

## Run

Open Actions → **Node Core OS — Real Linux 20–100 node full-mesh synchronization**
→ Run workflow. Start with 20, then 50, then 100.

The 100-node test needs 100 concurrently available GitHub-hosted runner slots
for its full-roster barrier to complete within the job timeout. `max-parallel`
is only a workflow cap; it does not increase the concurrency quota of the
GitHub account/organization. If the quota is below the requested matrix size,
jobs queue and the rendezvous barrier times out. Use an eligible larger
concurrency allowance or a self-hosted runner fleet with 100 separate Linux
machines/VMs. Do not interpret 100 matrix entries as 100 simultaneous nodes
unless 100 jobs actually start on separate runner hosts.

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
