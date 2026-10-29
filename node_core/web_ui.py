"""Local read-only web interface for Node Core OS.

Run from the repository root with:
    python -m node_core.web_ui

The first version intentionally exposes only status reads. It does not start,
stop, or reconfigure Kubo and does not expose the Kubo RPC API to the browser.
"""
from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from node_core.runtime import NodeRuntime

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
WEB_ROOT = Path(__file__).with_name("web")


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

    def _is_local_host_header(self) -> bool:
        host = self.headers.get("Host", "").strip().lower()
        return host in {
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
        }

    def _send_bytes(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'")
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

        if path == "/api/status":
            try:
                payload = {
                    "application": "Node Core OS byLAEV",
                    "web_interface": "running",
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

        if path == "/favicon.ico":
            self._send_bytes(HTTPStatus.NO_CONTENT, b"", "image/x-icon")
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

    def do_POST(self) -> None:  # noqa: N802 - no state-changing web actions in MVP
        self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "This initial web interface is read-only."})

    def log_message(self, format: str, *args: object) -> None:
        # Keep local logs useful while avoiding terminal control sequences.
        message = format % args
        print(f"[Node Core Web] {self.client_address[0]} - {message}")


def main() -> None:
    port = _port_from_environment()
    runtime = NodeRuntime()
    # Do not call runtime.boot() here: the first web milestone is a read-only
    # dashboard and must not silently start services or modify system state.
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
    print("Mode: read-only status; Kubo is not started or reconfigured by this server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Node Core OS web interface...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
