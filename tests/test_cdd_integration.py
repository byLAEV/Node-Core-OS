"""Loopback integration tests for three CDD gateways, failover, shared quota and policy checks.

The three gateway HTTP servers are independent listeners, but the shared quota
object is deliberately in-process. This validates the gateway integration seam;
it does NOT prove cross-process or cross-machine distributed quota coordination.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import math
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
from urllib.request import Request, urlopen

from node_core.identity.node_identity import NodeIdentityStore
from node_core.security.cdd import SlidingWindowRateLimiter, create_signed_policy
from node_core.security.cdd_gateway import (
    CDDGatewayConfig,
    CDDGatewayError,
    create_cdd_server,
    load_policy_from_kubo,
    make_cdd_handler,
    publish_policy_to_kubo,
)
from node_core.security.cdd_router import create_cdd_router_server


ORIGIN_TOKEN = "integration-lab-origin-token-more-than-32-bytes"


class ProtectedOriginHandler(BaseHTTPRequestHandler):
    """Synthetic Web2 origin that independently rejects direct access."""

    def log_message(self, format, *args):
        return

    def do_GET(self):
        supplied = self.headers.get("X-Node-Core-Origin-Token", "")
        if not hmac.compare_digest(supplied, ORIGIN_TOKEN):
            body = b"origin access denied"
            self.send_response(403)
        else:
            body = ("origin:" + self.path).encode()
            self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class MemoryKubo:
    """Minimal deterministic Kubo test double; not a real Kubo daemon."""

    cid = "b" + "a" * 20

    def __init__(self):
        self.payload = None
        self.pinned = False

    def add_file(self, path, *, pin=False, cid_version=1, cid_base="base32"):
        self.payload = Path(path).read_bytes()
        self.pinned = pin
        return type("Added", (), {"cid": self.cid})()

    def cat(self, cid):
        if cid != self.cid or self.payload is None:
            raise ValueError("CID not found")
        return self.payload


def request(url, *, timeout=2.0):
    started = time.perf_counter()
    req = Request(url, method="GET")
    try:
        response = urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc
    elapsed = time.perf_counter() - started
    with response:
        return response.status, response.read(), elapsed


class CDDThreeGatewayIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cdd-three-gateway-")
        self.addCleanup(self.temp.cleanup)
        identity = NodeIdentityStore(Path(self.temp.name) / "issuer")
        metadata = identity.initialize()
        self.trusted = {metadata["node_id"]: metadata["public_key"]}
        self.now = datetime.now(timezone.utc)
        self.identity = identity
        self.origin = None
        self.origin_thread = None
        self.gateways = []
        self.router = None
        self.router_thread = None
        self.count_lock = threading.Lock()
        self.gateway_counts = {"gateway-a": 0, "gateway-b": 0, "gateway-c": 0}

        self.policy = self.make_policy(sequence=1, max_requests=1000)
        self.origin = ThreadingHTTPServer(("127.0.0.1", 0), ProtectedOriginHandler)
        self.origin.daemon_threads = True
        self.origin_thread = threading.Thread(target=self.origin.serve_forever, daemon=True)
        self.origin_thread.start()

        self.shared_limiter = SlidingWindowRateLimiter()
        self.gateway_urls = []
        for gateway_name in ("gateway-a", "gateway-b", "gateway-c"):
            config = CDDGatewayConfig(
                origin_url=f"http://127.0.0.1:{self.origin.server_port}",
                service_id="web2:integration.test",
                origin_id="origin:integration.test",
                policy=self.policy,
                trusted_issuer_keys=self.trusted,
                last_sequence=0,
                timeout_seconds=1.5,
                origin_auth_token=ORIGIN_TOKEN,
            )
            base_handler = make_cdd_handler(config, limiter=self.shared_limiter)
            counts = self.gateway_counts
            count_lock = self.count_lock

            class InstrumentedGateway(base_handler):
                def do_GET(self, name=gateway_name):
                    with count_lock:
                        counts[name] += 1
                    super().do_GET()

            server = ThreadingHTTPServer(("127.0.0.1", 0), InstrumentedGateway)
            server.daemon_threads = True
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.gateways.append((server, thread, gateway_name))
            self.gateway_urls.append(f"http://127.0.0.1:{server.server_port}")

        self.router = create_cdd_router_server(("127.0.0.1", 0), self.gateway_urls)
        self.router_thread = threading.Thread(target=self.router.serve_forever, daemon=True)
        self.router_thread.start()
        self.base = f"http://127.0.0.1:{self.router.server_port}"

    def tearDown(self):
        if self.router is not None:
            self.router.shutdown()
            self.router.server_close()
        if self.router_thread is not None:
            self.router_thread.join(timeout=2)
        for server, thread, _name in self.gateways:
            try:
                server.shutdown()
            except (RuntimeError, OSError):
                pass
            server.server_close()
            thread.join(timeout=2)
        if self.origin is not None:
            self.origin.shutdown()
            self.origin.server_close()
        if self.origin_thread is not None:
            self.origin_thread.join(timeout=2)
        self.temp.cleanup()

    def make_policy(self, *, sequence, max_requests, issued_at=None, expires_at=None):
        issued_at = issued_at or self.now - timedelta(seconds=1)
        expires_at = expires_at or self.now + timedelta(minutes=5)
        return create_signed_policy(
            self.identity,
            service_id="web2:integration.test",
            sequence=sequence,
            issued_at=issued_at,
            expires_at=expires_at,
            max_requests=max_requests,
            window_seconds=30,
            max_body_bytes=1024,
            origin_id="origin:integration.test",
        )

    def test_round_robin_distributes_90_requests_across_three_gateways(self):
        latencies = []
        statuses = []
        errors = 0
        rounds = 3
        requests_per_round = 30
        total = rounds * requests_per_round
        for round_number in range(rounds):
            round_statuses = []
            for index in range(requests_per_round):
                request_number = round_number * requests_per_round + index
                try:
                    status, body, elapsed = request(
                        f"{self.base}/distribution/{request_number}"
                    )
                    statuses.append(status)
                    round_statuses.append(status)
                    latencies.append(elapsed)
                    self.assertEqual(
                        body, f"origin:/distribution/{request_number}".encode()
                    )
                except (OSError, TimeoutError) as exc:
                    errors += 1
                    self.fail(
                        f"Unexpected transport error at request {request_number}: {exc}"
                    )
            self.assertEqual(round_statuses.count(200), requests_per_round)

        self.assertEqual(errors, 0)
        self.assertEqual(statuses.count(200), total)
        self.assertEqual(sum(self.gateway_counts.values()), total)
        for gateway_name in ("gateway-a", "gateway-b", "gateway-c"):
            self.assertGreater(self.gateway_counts[gateway_name], 0)

        sorted_latencies = sorted(latencies)
        p95_index = max(0, math.ceil(0.95 * len(sorted_latencies)) - 1)
        self.metrics = {
            "rounds": rounds,
            "requests": total,
            "successes": statuses.count(200),
            "transport_errors": errors,
            "availability_percent": 100.0 * statuses.count(200) / total,
            "latency_ms_mean": 1000.0 * sum(latencies) / len(latencies),
            "latency_ms_p95": 1000.0 * sorted_latencies[p95_index],
            "gateway_counts": dict(self.gateway_counts),
        }
        print("CDD_THREE_GATEWAY_METRICS=" + json.dumps(self.metrics, sort_keys=True))
        self.assertEqual(self.metrics["availability_percent"], 100.0)
        self.assertLess(self.metrics["latency_ms_p95"], 2000.0)

    def test_failover_recovers_when_first_gateway_is_deliberately_stopped(self):
        failed_server, failed_thread, failed_name = self.gateways[0]
        failed_server.shutdown()
        failed_server.server_close()
        failed_thread.join(timeout=2)

        started = time.perf_counter()
        status, body, elapsed = request(f"{self.base}/failover")
        measured = time.perf_counter() - started
        self.assertEqual(status, 200)
        self.assertEqual(body, b"origin:/failover")
        self.assertLess(measured, 2.0)
        self.assertGreater(sum(self.gateway_counts.values()), 0)
        self.metrics = {
            "failed_gateway": failed_name,
            "recovery_seconds": measured,
            "request_latency_ms": elapsed * 1000.0,
            "recovered": True,
            "status": status,
        }

    def test_shared_limiter_rejects_quota_evasion_across_gateways(self):
        # A single limiter instance is injected into all three gateway handlers.
        # Requests arrive through different gateways but share the same route/client key.
        limited_policy = self.make_policy(sequence=2, max_requests=6)
        limited_config = CDDGatewayConfig(
            origin_url=f"http://127.0.0.1:{self.origin.server_port}",
            service_id="web2:integration.test",
            origin_id="origin:integration.test",
            policy=limited_policy,
            trusted_issuer_keys=self.trusted,
            origin_auth_token=ORIGIN_TOKEN,
        )
        # Reconfigure each handler's limiter/policy by using a dedicated second pool.
        limited_limiter = SlidingWindowRateLimiter()
        limited_urls = []
        limited_servers = []
        for _index in range(3):
            handler = make_cdd_handler(limited_config, limiter=limited_limiter)
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            server.daemon_threads = True
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            limited_servers.append((server, thread))
            limited_urls.append(f"http://127.0.0.1:{server.server_port}")
        limited_router = create_cdd_router_server(("127.0.0.1", 0), limited_urls)
        limited_router_thread = threading.Thread(target=limited_router.serve_forever, daemon=True)
        limited_router_thread.start()
        try:
            limited_base = f"http://127.0.0.1:{limited_router.server_port}"
            statuses = [request(f"{limited_base}/same-route")[0] for _ in range(10)]
            self.assertEqual(statuses.count(200), 6)
            self.assertEqual(statuses.count(429), 4)
        finally:
            limited_router.shutdown()
            limited_router.server_close()
            limited_router_thread.join(timeout=2)
            for server, thread in limited_servers:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_origin_rejects_direct_access_without_gateway_authentication(self):
        status, body, _elapsed = request(
            f"http://127.0.0.1:{self.origin.server_port}/direct"
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, b"origin access denied")

    def test_cid_policy_load_accepts_signed_manifest_and_rejects_tampering(self):
        kubo = MemoryKubo()
        cid = publish_policy_to_kubo(kubo, self.policy)
        self.assertTrue(kubo.pinned)
        loaded = load_policy_from_kubo(
            kubo, cid, self.trusted, last_sequence=0, now=self.now
        )
        self.assertEqual(loaded, self.policy)

        tampered = json.loads(kubo.payload.decode("utf-8"))
        tampered["limits"]["max_requests"] = 7
        kubo.payload = json.dumps(tampered).encode("utf-8")
        with self.assertRaises(CDDGatewayError):
            load_policy_from_kubo(
                kubo, cid, self.trusted, last_sequence=0, now=self.now
            )

    def test_expired_signed_policy_is_rejected_before_gateway_start(self):
        expired = self.make_policy(
            sequence=3,
            max_requests=1000,
            issued_at=self.now - timedelta(minutes=2),
            expires_at=self.now - timedelta(minutes=1),
        )
        config = CDDGatewayConfig(
            origin_url=f"http://127.0.0.1:{self.origin.server_port}",
            service_id="web2:integration.test",
            origin_id="origin:integration.test",
            policy=expired,
            trusted_issuer_keys=self.trusted,
            origin_auth_token=ORIGIN_TOKEN,
        )
        with self.assertRaises(CDDGatewayError):
            create_cdd_server(("127.0.0.1", 0), config)


if __name__ == "__main__":
    unittest.main()
