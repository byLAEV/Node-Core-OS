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
