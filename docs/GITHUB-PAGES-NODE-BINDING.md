# GitHub Page ↔ personal Node binding (functional phase 1)

This phase establishes one explicit association per Node Core OS installation:

- the operator's GitHub account,
- the GitHub App installation identifier (recorded when supplied),
- the operator-owned client repository,
- the GitHub Pages URL published from that repository,
- the persistent technical `node_id`.

The node identity comes from `NodeIdentityStore`; the binding is stored in
`~/.node-core/identity/github-binding/binding.json`.

## Configure

Run Node Core OS as the regular device user and authenticate GitHub CLI:

```sh
gh auth login
```

The binding manager is available to the local web API / Python runtime. Configure
with the GitHub login and a repository owned by that login. The Pages URL is
derived as `https://LOGIN.github.io/REPOSITORY/`.

## Record flow

A page record is first written as readable JSON into the node's local outbox.
The node then calls `GitHubNodeBinding.sync()`, verifies repository ownership
through GitHub API, and appends each record as a separate file under
`records/YYYY/MM/UUID.json` in that operator's repository. This avoids a shared
index file and makes every record independently addressable.

## Current implementation boundary

- The repository binding, node ID association, local outbox and GitHub Contents
  API write path are implemented as a first functional step.
- `github_app_installation_id` is recorded as configuration only. This version
  still uses the operator's authenticated `gh auth token`; it does not yet
  perform GitHub App installation-token exchange or Device Flow.
- The local web server currently binds to loopback. A remotely visited GitHub
  Page cannot submit to it until a public HTTPS relay / reachable node API is
  implemented and configured.
- Records are intentionally readable JSON in this phase. Use synthetic test
  data only. Encryption, privacy controls and production hardening are deferred.
- GitHub Pages is static hosting; the node is the writer and GitHub repository
  is the operator-specific accumulation store.

## Web API and static Page client

The local web interface exposes these first-phase routes:

- `GET /api/github/binding`: current account/repository/Page/node association.
- `POST /api/github/configure`: save the association.
- `POST /api/github/records`: append one readable JSON record to the local outbox.
- `GET /api/github/records`: inspect pending local records.
- `POST /api/github/sync`: append pending records to the configured GitHub repository.
- `POST /api/github/export`: export the static client template with `node-core-client.json`.

The BIOS web panel can configure, inspect, export and synchronize the association. The static template in `client-template/` reads its exported configuration and submits form records to the configured Node API.

### HTTPS reverse proxy / tunnel

The server continues to bind to `127.0.0.1`. For an Internet-hosted GitHub Page to reach it, forward the API through an HTTPS reverse proxy or tunnel to the loopback listener. Set:

```sh
export NODE_CORE_WEB_ALLOWED_HOSTS="node.example.com"
export NODE_CORE_WEB_ALLOWED_ORIGINS="https://operator.github.io"
```

Use the actual public hostname and exact Pages origin. Restart the web server after changing these values. The proxy must forward the original `Host` and `Origin` headers. The server does not automatically create a public tunnel or change router/firewall settings.

### GitHub write credentials

The first-phase sync uses the operator's GitHub CLI authentication. Authenticate locally with `gh auth login`; the visitor's browser never receives that token. The configured GitHub App installation ID is metadata only in this phase; GitHub App token exchange and Device Flow remain future work.

### Known functional limits

- Public visitor submissions are intentionally unauthenticated in this development phase. Only use synthetic test data.
- The Node API must be reachable through an operator-configured HTTPS proxy/tunnel.
- No automatic background sync is started; the operator invokes sync from the web panel or API.
- The static Page cannot write to GitHub directly; it sends data to the node.
- No privacy, encryption, identity proof, abuse prevention, or production security controls are included yet.

## Operator GitHub account and GitHub App

The local web interface supports GitHub App Device Flow:

1. Create a GitHub App and enable **Device Flow** in its settings.
2. Set `NODE_CORE_GITHUB_APP_CLIENT_ID` to the App's Client ID before starting the Node Core OS web interface.
3. In the local web panel, click **Vincular cuenta GitHub**.
4. Open the displayed GitHub verification URL, enter the one-time user code, and authorize the App.
5. Click **Comprobar autorización**. The node checks the authenticated account and stores the operator token data locally.
6. Install the GitHub App on the operator's client repository and enter its numeric installation ID in the binding form.
7. Set `NODE_CORE_GITHUB_APP_ID` to the App ID and `NODE_CORE_GITHUB_APP_PRIVATE_KEY` to the path of the downloaded PEM private key.
8. Configure the repository binding and run synchronization.

The device authorization token identifies the operator; it is not used as the repository write credential. Repository writes use a short-lived GitHub App installation token generated with the App ID/private key and restricted to the configured repository name and `contents: write` permission. If App settings are incomplete, synchronization falls back to the operator's authenticated GitHub CLI session.

Required environment variables for the App path:

```sh
export NODE_CORE_GITHUB_APP_CLIENT_ID="Iv1..."
export NODE_CORE_GITHUB_APP_ID="123456"
export NODE_CORE_GITHUB_APP_PRIVATE_KEY="$HOME/.node-core/github-app-private-key.pem"
```

Keep the PEM file on the operator's node. Do not put it in the client repository or GitHub Pages. The private key is not read until an App installation token is requested.

Device Flow endpoints:

- `POST /api/github/device/start`
- `POST /api/github/device/poll`
- `GET /api/github/device/status`

The browser does not receive the access token or App private key. This is a functional integration stage, not a complete security review; protect the node's local data directory and do not use real personal information during development.


## Replicating records to explicitly trusted Node Core peers

A node can replicate a locally owned Page record to another trusted Node Core node. The receiver stores a copy under:

```text
~/.node-core/storage/shared/github-record-replicas/<origin-node-id>/<record-uuid>.json
```

This is a replica in the receiving node's shared storage. It does not modify the receiver's GitHub repository. The original operator's repository remains the source repository for records submitted through that operator's Page.

The replication event uses the existing native P2P authenticated TLS session and signed/encrypted message transport. The receiver checks the authenticated sender node ID, recipient node ID, record owner, repository, event ID and record UUID before persisting. Repeated delivery of the same origin + record ID is idempotent; a conflicting record with the same ID is rejected.

### Pinning peer message keys

Each peer must already be explicitly trusted by its Node Core certificate. RSA message public keys are separate from the TLS/node identity and must be exchanged and fingerprint-verified out of band. After the peer's RSA public key fingerprint has been verified, pin it locally through the runtime method `trust_peer_message_key(node_id, public_key_pem)`. Pinned keys are stored in `~/.node-core/p2p/trusted-message-keys.json`.

The native P2P listener accepts replication events only from peers with a pinned RSA message key. The receiving callback writes records to local shared storage before the sender receives the signed acceptance receipt.

This is a two-node replication primitive, not global automatic propagation. The operator must select a trusted peer and invoke replication. Multi-hop forwarding, automatic fan-out, conflict resolution across repositories and public WAN rendezvous remain separate work.


## Persistent record replication

Records successfully written to the operator GitHub repository are retained in the node-local `identity/github-binding/archive/` directory. The runtime can replicate those archived records to one explicitly trusted Node Core peer with `replicate_synced_github_records(host, port, peer_node_id)`. Each receiving node stores a replica under `storage/shared/github-record-replicas/`; it does not write the record into its own operator GitHub repository.

The receiving native P2P listener uses the existing authenticated TLS service and pinned RSA message keys. Configure a peer's RSA key only after verifying its SHA-256 fingerprint out of band by calling `trust_peer_message_key(node_id, public_key_pem)`. The sender receives a signed receipt only after the receiver persists the record. Duplicate delivery is accepted without creating duplicate files.
