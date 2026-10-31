# GitHub App, GitHub Pages and personal Node binding

This functional phase connects one operator's GitHub account, GitHub App
installation, static Pages client, repository and personal Node Core OS node.

## Operator setup

Run Node Core OS as the normal device user. Do not use `sudo` or `su`.

1. Open **Node Core BIOS → GitHub Node Binding (menu 13)**.
2. Start GitHub App Device Flow using the GitHub App Client ID.
3. Open the displayed GitHub verification URL, enter the one-time code and authorize the App.
4. Return to BIOS and poll the Device Flow until the operator account is confirmed.
5. Configure the repository owned by that account, the GitHub Pages URL, the numeric App installation ID and the public HTTPS Node API URL.
6. Export the static client package.
7. Commit the exported files to the operator's own repository and enable GitHub Pages for that repository.

The node's persistent `node_id` comes from `NodeIdentityStore`. The binding is
stored locally at `~/.node-core/identity/github-binding/binding.json`.
The exported `node-core-client.json` contains the public account, repository,
Pages URL, node ID and Node API URL. It does not contain a GitHub access token
or App private key.

## Start the Node API

Open **Node Core BIOS → Services**:

- Option 5 starts the local Node Core Web API.
- Option 6 stops it.
- Option 7 displays its log.

The service manager starts and stops the web API as the current unprivileged
user. The web server listens on loopback at `127.0.0.1:8765` by default. It is
not exposed directly to the LAN or Internet.

For a GitHub Page hosted on the Internet, the operator must configure an HTTPS
reverse proxy or tunnel that forwards to the loopback listener. Configure the
public HTTPS URL in the GitHub Node Binding menu. The API derives the allowed
Host from that URL and the allowed Origin from the configured GitHub Pages URL.
Optional environment overrides can add proxy aliases or custom domains:

```sh
export NODE_CORE_WEB_ALLOWED_HOSTS="node.example.com"
export NODE_CORE_WEB_ALLOWED_ORIGINS="https://operator.github.io"
```

The reverse proxy must preserve the original `Host` and `Origin` headers.
The server does not create a public tunnel or modify router/firewall settings.
Do not expose the Python web server directly to the public Internet.

## Record flow

```text
Visitor's browser
    → operator's GitHub Pages client
    → operator's HTTPS Node API
    → local Node Core outbox
    → GitHub App installation token
    → operator's GitHub repository
    → Node Core OS replication to trusted peers
```

The static Page submits JSON to `POST /api/github/records`. The operator's
node stores each record in its local outbox. When the operator invokes sync,
Node Core verifies the repository owner and writes each record as a separate
file under `records/YYYY/MM/UUID.json` in that operator's repository. If the
GitHub API is unavailable, pending files remain in the local outbox for a
later retry.

The node uses a short-lived GitHub App installation token when all App
settings are configured:

- `NODE_CORE_GITHUB_APP_ID`: GitHub App numeric ID.
- `NODE_CORE_GITHUB_APP_PRIVATE_KEY`: filesystem path to the App PEM private key.
- The installation ID is configured in BIOS and restricted to the operator's
  selected repository with Contents write permission.

For development, if the App installation settings are incomplete, sync can
fall back to the operator's authenticated GitHub CLI session. Run
`gh auth login` locally on the node. The visitor's browser never receives
that token.

## Node-to-node replication

After records are synchronized, the operator can request replication to a
trusted Node Core peer from **GitHub Node Binding (menu 13)**. Native P2P uses
the node identities, trusted peer certificates and message keys already
configured in Node Core OS. Kubo/IPFS storage is a separate transport and
must not be confused with native P2P peers.

## API endpoints

- `GET /api/github/binding`: current operator account, repository, Pages and node association.
- `POST /api/github/device/start`: start GitHub App Device Flow.
- `POST /api/github/device/poll`: poll operator authorization.
- `POST /api/github/configure`: save the operator binding after Device Flow.
- `POST /api/github/records`: append a visitor record to the local outbox.
- `GET /api/github/records`: inspect pending local records.
- `POST /api/github/sync`: write pending records to the operator's repository.
- `POST /api/github/export`: export the static Pages client.

## Functional-phase boundaries

- Visitor submissions are unauthenticated and intended for synthetic test data only.
- Records are readable JSON in this phase; privacy, encryption, anti-spam and
  production access controls are intentionally deferred until the complete
  workflow has been demonstrated.
- No automatic background sync is started. The operator explicitly invokes sync.
- A GitHub Page is static hosting, not a backend. The Node API must be reachable
  through the operator's HTTPS proxy/tunnel.
- GitHub repository history retains prior commits. Deleting a record file does
  not erase previous versions from the repository history.
- Device Flow proves control of a GitHub account, not legal identity or a unique
  human being.
