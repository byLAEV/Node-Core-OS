"""Loopback-only multi-gateway router for CDD laboratory tests.

This router is not a public load balancer. It uses operator-configured gateway
URLs, round-robin ordering, bounded request/response sizes, and retries only
safe GET/HEAD requests after a gateway transport failure or 502/503/504.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from typing import Any, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_LAB_BODY_BYTES = 1_048_576
MAX_LAB_RESPONSE_BYTES = 2 * 1024 * 1024
_ALLOWED_METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade",
}
_RETRYABLE_STATUS = {502, 503, 504}


class CDDRouterError(ValueError):
    """Invalid multi-gateway laboratory router configuration."""


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class RoundRobinGatewayPool:
    """Thread-safe round-robin selection over a fixed list of gateway URLs."""

    def __init__(self, gateway_urls: Sequence[str]) -> None:
        if not isinstance(gateway_urls, (list, tuple)) or not gateway_urls:
            raise CDDRouterError("At least one configured gateway URL is required.")
        checked: list[str] = []
        for value in gateway_urls:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or parsed.path not in {"", "/"}
            ):
                raise CDDRouterError("Gateway entries must be absolute HTTP(S) base URLs.")
            checked.append(value.rstrip("/"))
        if len(set(checked)) != len(checked):
            raise CDDRouterError("Duplicate gateway URLs are not allowed.")
        self._urls = tuple(checked)
        self._index = 0
        self._lock = threading.Lock()

    @property
    def urls(self) -> tuple[str, ...]:
        return self._urls

    def next_order(self) -> tuple[str, ...]:
        with self._lock:
            start = self._index
            self._index = (self._index + 1) % len(self._urls)
        return self._urls[start:] + self._urls[:start]


def make_cdd_router_handler(gateway_urls: Sequence[str]):
    pool = RoundRobinGatewayPool(gateway_urls)
    opener = build_opener(_NoRedirectHandler())

    class CDDRouterHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "NodeCoreCDD-Router/0.1"
        sys_version = ""

        def log_message(self, format, *args: Any) -> None:
            return

        def _respond(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD" and body:
                self.wfile.write(body)

        def _handle(self) -> None:
            if self.command not in _ALLOWED_METHODS:
                self._respond(405, b"method not allowed")
                return
            parsed = urlsplit(self.path)
            if (
                not self.path.startswith("/")
                or self.path.startswith("//")
                or parsed.scheme
                or parsed.netloc
                or "\r" in self.path
                or "\n" in self.path
            ):
                self._respond(400, b"invalid request target")
                return
            if self.headers.get("Transfer-Encoding") is not None:
                self._respond(400, b"transfer-encoding is not supported by lab router")
                return
            try:
                body_length = int(self.headers.get("Content-Length", "0"))
            except (TypeError, ValueError):
                self._respond(400, b"invalid content-length")
                return
            if body_length < 0 or body_length > MAX_LAB_BODY_BYTES:
                self._respond(413, b"request body outside lab limit")
                return
            body = self.rfile.read(body_length) if body_length else b""
            if len(body) != body_length:
                self._respond(400, b"incomplete request body")
                return

            safe_to_retry = self.command in {"GET", "HEAD"}
            candidates = pool.next_order()
            last_error = None
            for index, base_url in enumerate(candidates):
                headers = {}
                for key, value in self.headers.items():
                    lowered = key.lower()
                    if lowered in _HOP_BY_HOP or lowered in {
                        "host", "content-length", "x-forwarded-for", "x-real-ip",
                        "forwarded", "x-node-core-client-id",
                    }:
                        continue
                    headers[key] = value
                if body:
                    headers["Content-Length"] = str(len(body))
                request = Request(
                    base_url + self.path,
                    data=body if self.command not in {"GET", "HEAD"} else None,
                    headers=headers,
                    method=self.command,
                )
                try:
                    response = opener.open(request, timeout=2.0)
                except HTTPError as exc:
                    response = exc
                except (URLError, TimeoutError, OSError, ValueError) as exc:
                    last_error = exc
                    if safe_to_retry:
                        continue
                    self._respond(502, b"gateway unavailable; unsafe request not retried")
                    return

                with response:
                    status = response.status
                    if safe_to_retry and status in _RETRYABLE_STATUS:
                        last_error = RuntimeError(f"gateway returned {status}")
                        continue
                    response_body = b"" if self.command == "HEAD" else response.read(
                        MAX_LAB_RESPONSE_BYTES + 1
                    )
                    if len(response_body) > MAX_LAB_RESPONSE_BYTES:
                        self._respond(502, b"gateway response exceeds lab limit")
                        return
                    self.send_response(status)
                    for key, value in response.headers.items():
                        lowered = key.lower()
                        if lowered in _HOP_BY_HOP or lowered in {
                            "content-length", "server", "connection",
                        }:
                            continue
                        self.send_header(key, value)
                    self.send_header("Content-Length", str(len(response_body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    if self.command != "HEAD" and response_body:
                        self.wfile.write(response_body)
                    return

            self._respond(503, b"all configured gateways unavailable")

        def do_GET(self) -> None:
            self._handle()

        def do_HEAD(self) -> None:
            self._handle()

        def do_POST(self) -> None:
            self._handle()

        def do_PUT(self) -> None:
            self._handle()

        def do_PATCH(self) -> None:
            self._handle()

        def do_DELETE(self) -> None:
            self._handle()

        def do_OPTIONS(self) -> None:
            self._handle()

        def do_CONNECT(self) -> None:
            self._respond(405, b"method not allowed")

        def do_TRACE(self) -> None:
            self._respond(405, b"method not allowed")

    return CDDRouterHandler


def create_cdd_router_server(
    address: tuple[str, int],
    gateway_urls: Sequence[str],
) -> ThreadingHTTPServer:
    """Create the lab router; use 127.0.0.1 in all tests."""
    handler = make_cdd_router_handler(gateway_urls)
    server = ThreadingHTTPServer(address, handler)
    server.daemon_threads = True
    return server
