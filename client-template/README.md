# Node Core Client

This is the static GitHub Pages client for one operator-owned Node Core OS repository.

## Export and publish

1. Start Node Core OS and authenticate the operator account with `gh auth login`.
2. Configure the binding through the local web API or Python runtime.
3. Set `node_api_url` to the public HTTPS URL that forwards to the operator's Node Core OS web server.
4. Export the client package from Node Core OS.
5. Copy the exported files into the operator's client repository and publish that repository with GitHub Pages.

The exported `node-core-client.json` binds the account, repository, Pages URL, node ID and Node API URL. The client submits records only to the configured node API. It does not receive or store the operator's GitHub token.

## Node API forwarding

The Node Core OS web server listens on loopback by default. To accept requests from a hosted GitHub Page, place a trusted HTTPS reverse proxy or tunnel in front of it. Configure:

- `NODE_CORE_WEB_ALLOWED_HOSTS`: comma-separated Host values accepted from the proxy.
- `NODE_CORE_WEB_ALLOWED_ORIGINS`: exact GitHub Pages origin, for example `https://operator.github.io`.

The reverse proxy must forward requests to the local server and preserve the configured Host and Origin headers. Do not expose the Python server directly to the public Internet.

## Record flow

GitHub Pages form → operator's Node Core OS API → readable local JSON outbox → explicit sync → operator's GitHub repository under `records/YYYY/MM/UUID.json`.

This first functional phase intentionally uses readable test data. It has no visitor authentication, privacy, encryption, anti-spam or production access controls. Do not collect real personal information. GitHub App installation ID is stored as metadata only; repository writes currently use the operator's authenticated GitHub CLI session (`gh auth login`).
