"""Local CDD HTTP gateway and Kubo-backed signed-policy helpers.

This is a laboratory reverse proxy. Bind it to loopback for tests. It is not a
production edge, global rate limiter, traffic distributor, or DDoS mitigation
service. The upstream origin is operator-configured and never client-selected.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from node_core.ipfs import KuboManager
from node_core.security.cdd import (
    SlidingWindowRateLimiter,
    canonical_json,
    verify_signed_policy,
)


MAX_POLICY_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_ALLOWED_METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


class CDDGatewayError(RuntimeError):
    """Raised when a CDD policy or gateway configuration is invalid."""


class _NoRedirectHandler(HTTPRedirectHandler):
    """Do not let an upstream redirect turn the configured origin into an open proxy."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def publish_policy_to_kubo(kubo: KuboManager, policy: Mapping[str, Any]) -> str:
    """Publish exact signed-policy JSON bytes through the existing KuboManager."""
    payload = canonical_json(dict(policy))
    if not payload or len(payload) > MAX_POLICY_BYTES:
        raise CDDGatewayError("CDD policy payload is empty or too large.")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix="node-core-cdd-policy-", suffix=".json", delete=False
        ) as handle:
            handle.write(payload)
            temporary_path = Path(handle.name)
        added = kubo.add_file(temporary_path, pin=True, cid_version=1, cid_base="base32")
        cid = getattr(added, "cid", None)
        if not isinstance(cid, str) or not cid:
            raise CDDGatewayError("Kubo did not return a CID for the signed policy.")
        return cid
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def load_policy_from_kubo(
    kubo: KuboManager,
    cid: str,
    trusted_issuer_keys: Mapping[str, str],
    *,
    last_sequence: int = 0,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fetch by CID, parse strictly, and reject any policy that fails signature checks."""
    if not isinstance(cid, str) or not cid or "/" in cid or " " in cid:
        raise CDDGatewayError("A single CID is required.")
    try:
        KuboManager._validate_cid(cid)
        raw = kubo.cat(cid)
    except (ValueError, RuntimeError) as exc:
        raise CDDGatewayError(f"Unable to retrieve CDD policy from Kubo: {exc}") from exc
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_POLICY_BYTES:
        raise CDDGatewayError("Kubo policy content is empty or exceeds the size limit.")
    try:
        policy = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CDDGatewayError("CID content is not valid UTF-8 JSON.") from exc
    if not isinstance(policy, dict):
        raise CDDGatewayError("CID content must be one JSON object.")
    if not verify_signed_policy(
        policy, trusted_issuer_keys, last_sequence=last_sequence, now=now
    ):
        raise CDDGatewayError("CDD policy signature, trust, freshness, or sequence is invalid.")
    return policy


@dataclass(frozen=True)
class CDDGatewayConfig:
    origin_url: str
    service_id: str
    origin_id: str
    policy: Mapping[str, Any]
    trusted_issuer_keys: Mapping[str, str]
    last_sequence: int = 0
    timeout_seconds: float = 3.0
    max_response_bytes: int = MAX_RESPONSE_BYTES
    origin_auth_token: str | None = None


def validate_gateway_config(config: CDDGatewayConfig, *, now: datetime | None = None) -> None:
    """Validate trust and bind the signed policy to the configured origin identity."""
    parsed = urlsplit(config.origin_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise CDDGatewayError("Origin must be an absolute HTTP(S) URL configured by the operator.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise CDDGatewayError("Origin URL must not contain credentials, query, or fragment.")
    if not config.service_id or not config.origin_id:
        raise CDDGatewayError("service_id and origin_id are required.")
    if config.policy.get("service_id") != config.service_id:
        raise CDDGatewayError("Signed policy is for a different service.")
    if config.policy.get("origin_id") != config.origin_id:
        raise CDDGatewayError("Signed policy is for a different origin.")
    if not verify_signed_policy(
        config.policy,
        config.trusted_issuer_keys,
        last_sequence=config.last_sequence,
        now=now,
    ):
        raise CDDGatewayError("CDD policy failed signature, trust, expiry, or sequence validation.")
    if not isinstance(config.timeout_seconds, (int, float)) or not 0 < config.timeout_seconds <= 30:
        raise CDDGatewayError("timeout_seconds must be greater than 0 and at most 30.")
    if config.origin_auth_token is not None and (
        not isinstance(config.origin_auth_token, str) or len(config.origin_auth_token) < 32
    ):
        raise CDDGatewayError("origin_auth_token must be at least 32 characters when configured.")
    if (
        isinstance(config.max_response_bytes, bool)
        or not isinstance(config.max_response_bytes, int)
        or not 1 <= config.max_response_bytes <= MAX_RESPONSE_BYTES
    ):
        raise CDDGatewayError("max_response_bytes is outside the supported range.")


def make_cdd_handler(
    config: CDDGatewayConfig,
    *,
    limiter: SlidingWindowRateLimiter | None = None,
):
    """Create a BaseHTTPRequestHandler class for a policy-enforcing lab gateway."""
    validate_gateway_config(config)
    request_limiter = limiter or SlidingWindowRateLimiter()
    limits = config.policy["limits"]
    opener = build_opener(_NoRedirectHandler())

    class CDDRequestHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "NodeCoreCDD/0.1"
        sys_version = ""

        def log_message(self, format, *args: Any) -> None:
            # Keep test logs deterministic and avoid logging request secrets.
            return

        def _respond(self, status: int, payload: bytes, *, content_type: str = "text/plain; charset=utf-8") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD" and payload:
                self.wfile.write(payload)

        def _handle(self) -> None:
            if self.command not in _ALLOWED_METHODS:
                self._respond(405, b"method not allowed")
                return

            parsed_target = urlsplit(self.path)
            if (
                not self.path.startswith("/")
                or self.path.startswith("//")
                or parsed_target.scheme
                or parsed_target.netloc
                or "\r" in self.path
                or "\n" in self.path
            ):
                self._respond(400, b"invalid request target")
                return

            # Do not trust client-supplied forwarding headers or identity headers.
            if self.headers.get("Transfer-Encoding") is not None:
                self._respond(400, b"transfer-encoding is not supported by this lab gateway")
                return
            raw_length = self.headers.get("Content-Length", "0")
            try:
                body_length = int(raw_length)
            except (TypeError, ValueError):
                self._respond(400, b"invalid content-length")
                return
            if body_length < 0:
                self._respond(400, b"invalid content-length")
                return
            if body_length > int(limits["max_body_bytes"]):
                self._respond(413, b"request body too large")
                return

            client_id = self.client_address[0]
            route = parsed_target.path or "/"
            if not request_limiter.allow(
                client_id,
                route,
                max_requests=int(limits["max_requests"]),
                window_seconds=int(limits["window_seconds"]),
            ):
                self._respond(429, b"request rate limit exceeded")
                return

            body = b""
            if body_length:
                body = self.rfile.read(body_length)
                if len(body) != body_length:
                    self._respond(400, b"incomplete request body")
                    return

            upstream_url = config.origin_url.rstrip("/") + self.path
            outgoing_headers = {}
            for key, value in self.headers.items():
                lowered = key.lower()
                if lowered in _HOP_BY_HOP or lowered in {
                    "host", "content-length", "x-forwarded-for", "x-real-ip",
                    "forwarded", "x-node-core-client-id",
                }:
                    continue
                outgoing_headers[key] = value
            if body:
                outgoing_headers["Content-Length"] = str(len(body))
            if config.origin_auth_token is not None:
                outgoing_headers["X-Node-Core-Origin-Token"] = config.origin_auth_token

            upstream = Request(
                upstream_url,
                data=body if self.command not in {"GET", "HEAD"} else None,
                headers=outgoing_headers,
                method=self.command,
            )
            try:
                response_context = opener.open(upstream, timeout=config.timeout_seconds)
            except HTTPError as exc:
                # Preserve upstream status codes without following redirects.
                response_context = exc
            except (URLError, TimeoutError, OSError, ValueError):
                self._respond(502, b"upstream unavailable")
                return

            with response_context as response:
                response_body = b"" if self.command == "HEAD" else response.read(
                    config.max_response_bytes + 1
                )
                if len(response_body) > config.max_response_bytes:
                    self._respond(502, b"upstream response exceeds lab limit")
                    return
                self.send_response(response.status)
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

    return CDDRequestHandler


def create_cdd_server(
    address: tuple[str, int],
    config: CDDGatewayConfig,
    *,
    limiter: SlidingWindowRateLimiter | None = None,
) -> ThreadingHTTPServer:
    """Create the lab server; callers should bind to 127.0.0.1 during tests."""
    handler = make_cdd_handler(config, limiter=limiter)
    server = ThreadingHTTPServer(address, handler)
    server.daemon_threads = True
    return server
