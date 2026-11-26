# Personal Node Relay Delivery Test

This is the first real GitHub Actions-to-Termux delivery path. GitHub's HTTPS API and a dedicated repository branch act as the relay; Termux initiates outbound HTTPS polling, so no inbound port on the phone is required. This is a test transport, not the native P2P protocol and not a claim of global decentralized discovery.

## What is verified

1. GitHub Actions creates a synthetic JSON request with a unique workflow run ID.
2. The request contains a SHA-256 digest and HMAC-SHA-256 authentication tag.
3. The Termux client validates the HMAC and digest before writing anything.
4. The node atomically stores the request at `$NODE_CORE_DATA_DIR/storage/relay/inbox/<run_id>.json` (normally `~/.node-core/storage/relay/inbox/`).
5. The receiver signs a receipt using the node's existing Ed25519 private key.
6. Actions checks the exact run ID, payload digest, pinned public key, derived node ID, and Ed25519 signature. Publishing a request without this receipt does **not** pass the workflow.

The test payload contains no personal identity data. The relay branch may be publicly readable in a public repository; use only synthetic test payloads.

## One-time setup

### 1. Configure GitHub Actions secrets

In the repository, open **Settings → Secrets and variables → Actions → New repository secret**.

Generate a 32-byte shared relay key on Termux:

```bash
openssl rand -hex 32
```

Save that exact 64-character hexadecimal value as the repository secret `NODE_CORE_RELAY_HMAC_KEY`. Do not commit it or paste it into workflow files.

Get the public key of the personal Node Core OS technical identity (this prints only the public key):

```bash
python -c 'from node_core.config import NodeConfig; from node_core.identity.node_identity import NodeIdentityStore; print(NodeIdentityStore(NodeConfig.load().data_dir).initialize()["public_key"])'
```

Save the resulting 64-character hexadecimal public key as `NODE_CORE_RELAY_NODE_PUBLIC_KEY`. This pins which node is allowed to satisfy the test; it is not a private key.

### 2. Prepare the Termux client

Update Node Core OS to a revision containing this feature, then from the repository directory run:

```bash
python -m pip install --disable-pip-version-check -r requirements.txt
export NODE_CORE_RELAY_REPO=byLAEV/Node-Core-OS
read -rsp 'Relay HMAC key (64 hex chars): ' NODE_CORE_RELAY_HMAC_KEY; echo
export NODE_CORE_RELAY_HMAC_KEY
read -rsp 'Fine-grained GitHub token with Contents read/write for this repository: ' NODE_CORE_RELAY_GITHUB_TOKEN; echo
export NODE_CORE_RELAY_GITHUB_TOKEN
python scripts/node_core_relay_client.py
```

Create a **fine-grained personal access token** restricted to this repository and the **Contents: Read and write** permission only. It is needed because the phone must publish its signed receipt back to the relay. Treat it as a credential; do not share it or put it in the repository. Keep this process running while Actions runs the test. Press Ctrl+C to stop polling.

The client uses outbound HTTPS only and writes accepted payloads under the configured Node Core OS data directory. It does not open a network listener. Do not run the test with personal identity records.

## Run the real test

After the workflow is available on the default branch:

1. Open **Actions → Node Core OS — Personal Node Relay Delivery → Run workflow**.
2. Keep the Termux client running.
3. Wait for the workflow to finish.

The workflow passes only if the phone publishes a valid Ed25519 receipt for that exact run ID and payload hash before the timeout. On the phone, expect a line beginning `RECEIPT PUBLISHED`; in Actions, expect `RECEIVER_CONFIRMED` and a green workflow result. A timeout or invalid receipt is a failed delivery, not a partial pass.

## Relay data and limitations

The branch `node-core-relay` contains `.node-core-relay/requests/` and `.node-core-relay/receipts/`. Request and receipt records are retained as Git commits, so this initial proof is not a queue with automatic expiry. Remove test records/branch when no longer needed. A repository token with Contents write can modify repository content; the HMAC and pinned Ed25519 receipt protect message authenticity/integrity but do not make the GitHub branch private. This bridge is an initial verifiable delivery mechanism, not a substitute for native P2P or a deployed relay service.

## Troubleshooting

- **Actions says a secret is missing:** add both repository secrets exactly as named above.
- **Termux reports HMAC verification failed:** confirm the same 64-character key is used by Actions and Termux.
- **Actions times out:** check that the client is running, the GitHub token has Contents write permission, and the client can reach GitHub over HTTPS.
- **Node public key mismatch:** regenerate the configured value from the actual personal node's technical identity. Do not replace the node's private key.
