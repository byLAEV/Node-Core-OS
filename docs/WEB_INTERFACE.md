# Local web interface (first milestone)

The first milestone provides a **read-only** browser dashboard backed by the existing Node Core OS Python runtime. It displays the actual status returned by `NodeRuntime.kubo.status()`.

## Run

From the repository root, with the same Python environment used by Node Core OS:

```sh
python -m node_core.web_ui
```

Open:

```text
http://127.0.0.1:8765/
```

Stop the server with `Ctrl+C`.

If port 8765 is occupied, the server exits with an error instead of switching ports silently. An alternate port can be explicitly selected for a test:

```sh
NODE_CORE_WEB_PORT=8766 python -m node_core.web_ui
```

The web server always binds to `127.0.0.1`, not `0.0.0.0`. Do not expose it to a LAN or the public internet.

## Scope and safety

- The page calls the local `/api/status` endpoint.
- The endpoint reads the configured Kubo status through `NodeRuntime.kubo.status()`.
- The first milestone does not call `runtime.boot()`; starting the web server does not automatically start Kubo or native P2P services.
- The Kubo RPC API remains separate and is never proxied through the browser.
- POST requests are rejected. There are no state-changing actions in this milestone.
- Menu entries are intentionally disabled until each operation is connected to the existing runtime with its original input validation and confirmations.
- The configured Kubo API endpoint and repository path are shown as diagnostics, not treated as proof of reachability or successful content retrieval.

## Next implementation steps

1. Verify this dashboard on the target Termux installation.
2. Add a read-only route for the full main-menu network summary using existing runtime status methods.
3. Implement each menu as explicit, typed actions; do not route arbitrary command strings from the browser to a shell.
4. Add tests for every action and preserve the terminal UI.
