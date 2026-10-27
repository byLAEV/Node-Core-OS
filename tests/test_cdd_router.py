"""Loopback-only tests for multi-gateway distribution and failover."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest
import urllib.error
from urllib.request import Request, urlopen

from node_core.security.cdd_router import (
    CDDRouterError,
    RoundRobinGatewayPool,
    create_cdd_router_server,
)


class NamedGatewayHandler(BaseHTTPRequestHandler):
    name = "gateway"

    def log_message(self, format, *args):
        return

    def do_GET(self):
        body = (self.name + ":" + self.path).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_server(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def request(url, *, method="GET", data=None):
    req = Request(url, method=method, data=data)
    try:
        return urlopen(req, timeout=3)
    except urllib.error.HTTPError as exc:
        return exc


class CDDRouterTests(unittest.TestCase):
    def tearDown(self):
        for server, thread in getattr(self, "servers", []):
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def add_server(self, handler):
        if not hasattr(self, "servers"):
            self.servers = []
        server, thread = start_server(handler)
        self.servers.append((server, thread))
        return server

    def router(self, urls):
        self.router_server = create_cdd_router_server(("127.0.0.1", 0), urls)
        self.router_thread = threading.Thread(
            target=self.router_server.serve_forever, daemon=True
        )
        self.router_thread.start()
        if not hasattr(self, "servers"):
            self.servers = []
        self.servers.append((self.router_server, self.router_thread))
        return f"http://127.0.0.1:{self.router_server.server_port}"

    def test_round_robin_distributes_requests_across_two_gateways(self):
        class GatewayA(NamedGatewayHandler):
            name = "gateway-a"

        class GatewayB(NamedGatewayHandler):
            name = "gateway-b"

        a = self.add_server(GatewayA)
        b = self.add_server(GatewayB)
        base = self.router([
            f"http://127.0.0.1:{a.server_port}",
            f"http://127.0.0.1:{b.server_port}",
        ])
        results = []
        for _ in range(4):
            response = request(base + "/health")
            results.append(response.read().decode())
            self.assertEqual(response.status, 200)
        self.assertEqual(results, [
            "gateway-a:/health", "gateway-b:/health",
            "gateway-a:/health", "gateway-b:/health",
        ])

    def test_get_fails_over_when_first_gateway_is_unavailable(self):
        class HealthyGateway(NamedGatewayHandler):
            name = "healthy"

        healthy = self.add_server(HealthyGateway)
        unused = ThreadingHTTPServer(("127.0.0.1", 0), NamedGatewayHandler)
        bad_port = unused.server_port
        unused.server_close()
        base = self.router([
            f"http://127.0.0.1:{bad_port}",
            f"http://127.0.0.1:{healthy.server_port}",
        ])
        response = request(base + "/after-failure")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.read(), b"healthy:/after-failure")

    def test_post_is_not_retried_when_first_gateway_is_unavailable(self):
        class HealthyGateway(NamedGatewayHandler):
            name = "healthy"

        healthy = self.add_server(HealthyGateway)
        unused = ThreadingHTTPServer(("127.0.0.1", 0), NamedGatewayHandler)
        bad_port = unused.server_port
        unused.server_close()
        base = self.router([
            f"http://127.0.0.1:{bad_port}",
            f"http://127.0.0.1:{healthy.server_port}",
        ])
        response = request(base + "/write", method="POST", data=b"payload")
        self.assertEqual(response.status, 502)
        self.assertIn(b"unsafe request not retried", response.read())

    def test_router_rejects_empty_duplicate_or_non_base_urls(self):
        with self.assertRaises(CDDRouterError):
            RoundRobinGatewayPool([])
        with self.assertRaises(CDDRouterError):
            RoundRobinGatewayPool(["http://127.0.0.1:8000", "http://127.0.0.1:8000/"])
        with self.assertRaises(CDDRouterError):
            RoundRobinGatewayPool(["http://127.0.0.1:8000/path"])

    def test_router_rejects_oversized_request_body(self):
        class HealthyGateway(NamedGatewayHandler):
            name = "healthy"

        gateway = self.add_server(HealthyGateway)
        base = self.router([f"http://127.0.0.1:{gateway.server_port}"])
        req = Request(
            base + "/large",
            method="POST",
            data=b"x" * (1_048_576 + 1),
        )
        try:
            response = urlopen(req, timeout=3)
        except urllib.error.HTTPError as exc:
            response = exc
        self.assertEqual(response.status, 413)
        self.assertEqual(response.read(), b"request body outside lab limit")


if __name__ == "__main__":
    unittest.main()
