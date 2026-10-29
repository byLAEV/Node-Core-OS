# Local web interface (first milestone)

La primera etapa ofrece un panel web de **solo lectura** backed by the existing Node Core OS Python runtime. It displays the actual status returned by `NodeRuntime.kubo.status()`.

## Run

From the repository root, with the same Python environment used by Node Core OS:

```sh
python -m node_core.web_ui
```

Abre:

```text
http://127.0.0.1:8765/
```

Detén el servidor con `Ctrl+C`.

Si el puerto 8765 está ocupado, el servidor finaliza con un error en lugar de cambiar de puerto silenciosamente. Se puede elegir explícitamente otro puerto para una prueba:

```sh
NODE_CORE_WEB_PORT=8766 python -m node_core.web_ui
```

El servidor web siempre escucha en `127.0.0.1`, not `0.0.0.0`. No lo expongas a una LAN ni a internet público.

## Alcance y seguridad

- The page calls the local `/api/status` endpoint.
- The endpoint reads the configured Kubo status through `NodeRuntime.kubo.status()`.
- The first milestone does not call `runtime.boot()`; starting the web server does not automatically start Kubo or native P2P services.
- The Kubo RPC API remains separate and is never proxied through the browser.
- POST requests are rejected. There are no state-changing actions in this milestone.
- Menu entries are intentionally disabled until each operation is connected to the existing runtime with its original input validation and confirmations.
- The configured Kubo API endpoint and repository path are shown as diagnostics, not treated as proof of reachability or successful content retrieval.

## Siguientes pasos de implementación

1. Verify this dashboard on the target Termux installation.
2. Add a read-only route for the full main-menu network summary using existing runtime status methods.
3. Implement each menu as explicit, typed actions; do not route arbitrary command strings from the browser to a shell.
4. Add tests for every action and preserve the terminal UI.
