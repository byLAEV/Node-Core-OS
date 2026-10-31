"""Local web interface for Node Core OS.

Run from the repository root with:
    python -m node_core.web_ui

The interface exposes status reads and an explicit, confirmed Kubo start action.
It does not expose the Kubo RPC API to the browser.
"""
from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from node_core.github_binding import GitHubBindingError, GitHubNodeBinding
from node_core.github_app_auth import GitHubAppAuth, GitHubAppError
from node_core.identity.node_identity import NodeIdentityStore

from node_core.runtime import NodeRuntime

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
WEB_ROOT = Path(__file__).with_name("web")


def _require_unprivileged_user() -> None:
    """Refuse to run the web interface as root or through sudo."""
    get_effective_uid = getattr(os, "geteuid", None)
    if get_effective_uid is None:
        raise SystemExit(
            "Cannot verify the effective user ID on this platform; "
            "run Node Core OS web UI from a supported unprivileged environment."
        )
    if get_effective_uid() == 0:
        raise SystemExit(
            "Refusing to run Node Core OS web UI as root. "
            "Run it as the regular device user without sudo or su."
        )


def _auto_start_kubo_enabled() -> bool:
    """Return whether the operator explicitly enabled Kubo auto-start."""
    value = os.environ.get("NODE_CORE_WEB_AUTO_START_KUBO", "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"", "0", "false", "no", "off"}:
        return False
    raise ValueError(
        "NODE_CORE_WEB_AUTO_START_KUBO must be one of: 1, 0, true, false, yes, no, on, off."
    )


def _port_from_environment() -> int:
    raw = os.environ.get("NODE_CORE_WEB_PORT", str(DEFAULT_PORT))
    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError("NODE_CORE_WEB_PORT must be an integer from 1 to 65535.") from exc
    if not 1 <= port <= 65535:
        raise ValueError("NODE_CORE_WEB_PORT must be an integer from 1 to 65535.")
    return port


def _kubo_status(runtime: NodeRuntime) -> dict[str, Any]:
    """Serialize the actual KuboManager status without inventing availability."""
    status = runtime.kubo.status()
    if not status.installed:
        state = "not_installed"
    elif not status.initialized:
        state = "not_initialized"
    elif status.running:
        state = "running"
    else:
        state = "not_responding"

    return {
        "state": state,
        "installed": bool(status.installed),
        "initialized": bool(status.initialized),
        "running": bool(status.running),
        "peer_id": status.peer_id,
        "version": status.version,
        "detail": status.detail,
        "api": runtime.config.ipfs_api,
        "repo_path": str(runtime.config.ipfs_repo_path),
    }


class NodeCoreWebServer(ThreadingHTTPServer):
    """HTTP server bound to loopback only, sharing one runtime object."""

    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, port: int, runtime: NodeRuntime) -> None:
        self.runtime = runtime
        super().__init__((HOST, port), NodeCoreRequestHandler)


class NodeCoreRequestHandler(BaseHTTPRequestHandler):
    server: NodeCoreWebServer
    protocol_version = "HTTP/1.1"

    def _allowed_hosts(self) -> set[str]:
        hosts = {
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
        }
        configured = os.environ.get("NODE_CORE_WEB_ALLOWED_HOSTS", "")
        hosts.update(value.strip().lower() for value in configured.split(",") if value.strip())
        return hosts

    def _is_local_host_header(self) -> bool:
        host = self.headers.get("Host", "").strip().lower()
        return host in self._allowed_hosts()

    def _allowed_origins(self) -> set[str]:
        configured = os.environ.get("NODE_CORE_WEB_ALLOWED_ORIGINS", "")
        return {value.strip().rstrip("/") for value in configured.split(",") if value.strip()}

    def _origin_allowed(self) -> bool:
        origin = self.headers.get("Origin", "").strip().rstrip("/")
        local = {
            f"http://127.0.0.1:{self.server.server_port}",
            f"http://localhost:{self.server.server_port}",
        }
        return origin in local or origin in self._allowed_origins()

    def _binding(self) -> GitHubNodeBinding:
        runtime = self.server.runtime
        binding = getattr(runtime, "github_binding", None)
        if binding is None:
            binding = GitHubNodeBinding(runtime.config.data_dir, NodeIdentityStore(runtime.config.data_dir))
            runtime.github_binding = binding
        return binding

    def _read_json(self, maximum: int = 65536) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("Expected application/json.")
        length = int(self.headers.get("Content-Length", "0"))
        if not 1 <= length <= maximum:
            raise ValueError(f"Request body must be between 1 and {maximum} bytes.")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Request JSON must be an object.")
        return value

    def _send_bytes(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        origin = self.headers.get("Origin", "").strip().rstrip("/")
        if origin and self._origin_allowed():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self' https:; style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: HTTPStatus, value: dict[str, Any]) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if not self._is_local_host_header():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "Host header not allowed."})
            return

        path = urlsplit(self.path).path
        if path == "/":
            try:
                body = (WEB_ROOT / "index.html").read_bytes()
            except OSError:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Web interface file is missing."})
                return
            self._send_bytes(HTTPStatus.OK, body, "text/html; charset=utf-8")
            return

        if path in {"/style.css", "/app.js"}:
            asset_name = path.lstrip("/")
            content_type = "text/css; charset=utf-8" if asset_name.endswith(".css") else "text/javascript; charset=utf-8"
            try:
                body = (WEB_ROOT / asset_name).read_bytes()
            except OSError:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Web asset is missing."})
                return
            self._send_bytes(HTTPStatus.OK, body, content_type)
            return

        if path == "/api/status":
            try:
                payload = {
                    "application": "Node Core OS byLAEV",
                    "web_interface": "running",
                    "web_port": self.server.server_port,
                    "runtime": "loaded",
                    "kubo": _kubo_status(self.server.runtime),
                }
            except Exception as exc:  # Report diagnostic detail locally; don't hide it.
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"error": "Could not query Node Core OS runtime.", "detail": str(exc)},
                )
                return
            self._send_json(HTTPStatus.OK, payload)
            return

        if path == "/api/github/device/status":
            self._send_json(HTTPStatus.OK, GitHubAppAuth(self.server.runtime.config.data_dir).operator_status())
            return

        if path == "/api/github/binding":
            try:
                self._send_json(HTTPStatus.OK, self._binding().status())
            except Exception as exc:
                self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Could not read GitHub binding.", "detail": str(exc)})
            return

        if path == "/api/github/records":
            try:
                binding = self._binding()
                status = binding.status()
                records = []
                for record_path in sorted(binding.outbox.glob("*.json")):
                    records.append(json.loads(record_path.read_text(encoding="utf-8")))
                self._send_json(HTTPStatus.OK, {"binding": status, "records": records})
            except Exception as exc:
                self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Could not read local records.", "detail": str(exc)})
            return

        if path == "/api/network/kubo":
            try:
                kubo_status = self.server.runtime.kubo.status()
                payload: dict[str, Any] = {
                    "kubo_running": bool(kubo_status.running),
                    "peer_id": kubo_status.peer_id,
                    "version": kubo_status.version,
                    "connected_peers": [],
                    "peer_count": 0,
                    "detail": None,
                }
                if kubo_status.running:
                    network_status = self.server.runtime.network.status()
                    payload["peer_id"] = network_status.identity.peer_id
                    payload["connected_peers"] = list(network_status.connected_peers)
                    payload["peer_count"] = len(network_status.connected_peers)
                else:
                    payload["detail"] = "Kubo no está en ejecución; no se consultaron los pares."
            except Exception as exc:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"error": "No se pudo consultar el estado de red de Kubo.", "detail": str(exc)},
                )
                return
            self._send_json(HTTPStatus.OK, payload)
            return

        if path == "/favicon.ico":
            self._send_bytes(HTTPStatus.NO_CONTENT, b"", "image/x-icon")
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

    def do_OPTIONS(self) -> None:  # noqa: N802
        if not self._is_local_host_header() or not self._origin_allowed():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "Host or Origin not allowed."})
            return
        self._send_bytes(HTTPStatus.NO_CONTENT, b"", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if not self._is_local_host_header():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "Host header not allowed."})
            return

        if not self._origin_allowed():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "Origin not allowed."})
            return

        path = urlsplit(self.path).path
        if path in {"/api/github/device/start", "/api/github/device/poll", "/api/github/configure", "/api/github/records", "/api/github/sync", "/api/github/export"}:
            try:
                request_data = self._read_json()
                if path == "/api/github/device/start":
                    client_id = request_data.get("client_id") or os.environ.get("NODE_CORE_GITHUB_APP_CLIENT_ID", "")
                    result = GitHubAppAuth(self.server.runtime.config.data_dir).start_device_flow(client_id)
                    self._send_json(HTTPStatus.OK, result)
                    return
                if path == "/api/github/device/poll":
                    expected = request_data.get("expected_login") or self._binding().status().get("github_account")
                    result = GitHubAppAuth(self.server.runtime.config.data_dir).poll_device_flow(expected)
                    self._send_json(HTTPStatus.OK, result)
                    return
                binding = self._binding()
                if path == "/api/github/configure":
                    operator = GitHubAppAuth(self.server.runtime.config.data_dir).operator_status()
                    requested_login = str(request_data.get("github_login", "")).strip().lower()
                    if not operator.get("authorized") or requested_login != str(operator.get("github_login", "")).lower():
                        raise GitHubAppError("Complete GitHub App Device Flow for the same operator account before configuring this repository.")
                    result = binding.configure(
                        requested_login,
                        request_data.get("repository", ""),
                        request_data.get("pages_url"),
                        request_data.get("github_app_installation_id"),
                        request_data.get("node_api_url"),
                    )
                    self._send_json(HTTPStatus.OK, result)
                    return
                if path == "/api/github/records":
                    record = binding.add_record(request_data.get("fields"))
                    self._send_json(HTTPStatus.CREATED, record)
                    return
                if path == "/api/github/sync":
                    self._send_json(HTTPStatus.OK, binding.sync())
                    return
                target = request_data.get("target_dir") or str(Path.home() / "node-core-client")
                exported = binding.export_client_package(Path(target))
                self._send_json(HTTPStatus.OK, {"exported_directory": str(exported)})
                return
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError, GitHubBindingError, GitHubAppError) as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            except Exception as exc:
                self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "GitHub operation failed.", "detail": str(exc)})
                return

        if path != "/api/kubo/start":
            self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "This POST endpoint is not supported."})
            return

        try:
            request_data = self._read_json(4096)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if request_data.get("confirm") is not True:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Explicit confirmation is required to start Kubo."})
            return

        try:
            before = self.server.runtime.kubo.status()
            if not before.installed:
                self._send_json(HTTPStatus.CONFLICT, {
                    "error": "Kubo is not installed.",
                    "detail": "Install Kubo for this user before starting it from the web interface.",
                })
                return
            if before.running:
                self._send_json(HTTPStatus.OK, {
                    "message": "Kubo is already running.",
                    "kubo": _kubo_status(self.server.runtime),
                })
                return

            # KuboManager.start() uses the configured executable and IPFS_PATH,
            # starts the daemon as this same unprivileged user, and initializes
            # the configured repo only if the user explicitly confirmed above.
            self.server.runtime.kubo.start()
            status = self.server.runtime.kubo.status()
            if not status.running:
                self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {
                    "error": "Kubo start returned, but the API did not become available.",
                    "detail": status.detail or "Check the configured Kubo daemon log.",
                    "kubo": _kubo_status(self.server.runtime),
                })
                return
            self._send_json(HTTPStatus.OK, {
                "message": "Kubo started successfully.",
                "kubo": _kubo_status(self.server.runtime),
            })
        except Exception as exc:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {
                "error": "Could not start Kubo.",
                "detail": str(exc),
            })

    def log_message(self, format: str, *args: object) -> None:
        # Keep local logs useful while avoiding terminal control sequences.
        message = format % args
        print(f"[Node Core Web] {self.client_address[0]} - {message}")


def main() -> None:
    _require_unprivileged_user()
    try:
        port = _port_from_environment()
        auto_start_kubo = _auto_start_kubo_enabled()
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    runtime = NodeRuntime()
    try:
        server = NodeCoreWebServer(port, runtime)
    except OSError as exc:
        if getattr(exc, "errno", None) in {48, 98, 10048}:
            raise SystemExit(
                f"Port {port} is already in use on {HOST}. "
                "Stop the other listener or choose NODE_CORE_WEB_PORT explicitly."
            ) from exc
        raise

    print("Node Core OS byLAEV — local web interface")
    print(f"URL: http://{HOST}:{port}/")
    print("Binding: loopback only (not exposed to the LAN).")
    if auto_start_kubo:
        try:
            print("Kubo auto-start: enabled by NODE_CORE_WEB_AUTO_START_KUBO.")
            runtime.kubo.start()
            if not runtime.kubo.status().running:
                raise RuntimeError("Kubo start returned but its API is not responding.")
            print("Kubo status: running.")
        except Exception as exc:
            server.server_close()
            raise SystemExit(f"Automatic Kubo startup failed: {exc}") from exc
    else:
        print("Kubo auto-start: disabled (default). Use the web button or set NODE_CORE_WEB_AUTO_START_KUBO=1.")
    print("Kubo can also be started explicitly from the web interface after confirmation.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Node Core OS web interface...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
