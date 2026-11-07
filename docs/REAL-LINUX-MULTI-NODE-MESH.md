# Real Linux 20–200 node mesh test

Runs one independent GitHub-hosted Ubuntu 24.04 VM per node. Each VM installs
Node Core OS using installer/install.sh as the ordinary runner user.

## Required Tailscale setup

Create a Tailscale OAuth client with writable auth_keys scope and permission
to apply tag:node-core-ci. Merge a tag owner and ACL into the existing tailnet
policy (do not replace unrelated rules). Permit TCP 8765 and 46000 between
tagged nodes. Example policy fragment:

{
  "tagOwners": {"tag:node-core-ci": ["autogroup:admin"]},
  "acls": [{"action":"accept","src":["tag:node-core-ci"],"dst":["tag:node-core-ci:8765,46000"]}]
}

Add GitHub Actions secrets TS_OAUTH_CLIENT_ID and TS_OAUTH_SECRET. Never commit
credentials. Tailscale's official GitHub Action creates ephemeral devices.

## Run

Actions → Node Core OS — Real Linux 20–200 node P2P mesh → Run workflow.
Choose 20, 50, 100 or 200. GitHub runner concurrency must schedule the entire
matrix at once or the full-roster barrier will time out.

## Tested

- Separate Ubuntu 24.04 runner VMs and non-root users.
- Actual Node Core OS install on every VM.
- Unique Ed25519 identities and identity-bound TLS certificates.
- Temporary rendezvous registry on node 0; public metadata only, not payload relay.
- All nodes sign and verify the same canonical presence manifest.
- Existing mutual TLS, encrypted direct P2P messages and signed receipts.
- Two-hop directed mesh: every node sends two and receives two messages.
- Per-node JSON evidence with identity, OS, UID, hostname, overlay IP, manifest,
  sent messages and received messages.

Unanimous presence signatures are not Byzantine fault-tolerant state-machine
consensus. These VMs are separate cloud runners but share one CI provider and
are not 200 independent physical operators or geographically diverse hosts.
