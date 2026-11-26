# Node Core Client

This is the static GitHub Pages client for one operator-owned Node Core OS repository.

## Export and publish

1. Start Node Core OS as the normal device user.
2. Open **Node Core BIOS → GitHub Node Binding (menu 13)**.
3. Authorize the operator GitHub account through GitHub App Device Flow.
4. Configure the operator-owned repository, GitHub App installation ID and public HTTPS Node API URL.
5. Export the client package from BIOS.
6. Copy the exported files into that operator's repository, commit and enable GitHub Pages.

The exported `node-core-client.json` binds the GitHub account, repository, Pages URL, persistent node ID and Node API URL. The static page submits records only to the configured Node API. It does not receive or store the operator's GitHub access token or GitHub App private key.

## Start the Node API

Open **Node Core BIOS → Services**:

- Option 5 starts the local Node Core Web API.
- Option 6 stops it.
- Option 7 displays its log.

The server listens on loopback by default. To receive requests from an Internet-hosted GitHub Page, place an HTTPS reverse proxy or tunnel in front of the local server. The Node API derives its accepted Host from the configured Node API URL and its accepted Origin from the configured GitHub Pages URL. Optional environment overrides can add custom aliases:

- `NODE_CORE_WEB_ALLOWED_HOSTS`: additional comma-separated Host values.
- `NODE_CORE_WEB_ALLOWED_ORIGINS`: additional exact Pages origins.

The proxy must preserve the original Host and Origin headers. Do not expose the Python server directly to the public Internet.

## Record flow

GitHub Pages form → operator's Node Core OS API → readable local JSON outbox → immediate GitHub sync attempt → operator's GitHub repository under `records/YYYY/MM/UUID.json`. If GitHub is unavailable or the App is not configured, the record remains queued locally. The running Node API retries the queue every 30 seconds, and BIOS option 6 allows an immediate manual retry.

When the GitHub App installation ID, App ID and PEM private-key path are configured, Node Core OS creates a short-lived installation token scoped to the operator's repository. For development, sync can fall back to the operator's local `gh auth login` session. The visitor's browser never receives either credential.

## Functional-phase boundaries

This first functional phase intentionally uses readable synthetic test data. Visitor submissions are unauthenticated, and privacy, encryption, anti-spam and production access controls are deferred. Do not collect real personal information. GitHub Pages is static hosting; the operator's Node Core OS is the API and writer. GitHub stores each operator's records in that operator's own repository, and Node Core OS can replicate synchronized records to explicitly trusted peers.
