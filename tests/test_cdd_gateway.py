"""Local integration tests for the CDD HTTP gateway and Kubo policy adapter."""
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import threading
import unittest
import urllib.error
from urllib.request import Request, urlopen
import tempfile
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.security.cdd import create_signed_policy
from node_core.security.cdd_intent import CDDIntentLobby, IntentRoute
from node_core.security.cdd_gateway import (
    CDDGatewayConfig,
    CDDGatewayError,
    create_cdd_server,
    load_policy_from_kubo,
    publish_policy_to_kubo,
)


class FakeKubo:
    def __init__(self):
        self.cid = "b" + "a" * 20
        self.payload = None
        self.pinned = None

    def add_file(self, path, *, pin=False, cid_version=1, cid_base="base32"):
        self.payload = Path(path).read_bytes()
        self.pinned = pin
        return type("Added", (), {"cid": self.cid})()

    def cat(self, cid):
        if cid != self.cid or self.payload is None:
            raise ValueError("CID not found")
        return self.payload


class OriginHandler(BaseHTTPRequestHandler):
    token = "test-origin-token-with-more-than-32-characters"

    def log_message(self, format, *args):
        return

    def _authorized(self):
        supplied = self.headers.get("X-Node-Core-Origin-Token", "")
        if not hmac.compare_digest(supplied, self.token):
            payload = b"origin access denied"
            self.send_response(403)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return False
        return True

    def do_GET(self):
        if not self._authorized():
            return
        payload = ("origin:" + self.path).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if not self._authorized():
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class CDDGatewayIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cdd-gateway-test-")
        self.addCleanup(self.temp.cleanup)
        self.identity = NodeIdentityStore(Path(self.temp.name) / "issuer")
        metadata = self.identity.initialize()
        self.trusted = {metadata["node_id"]: metadata["public_key"]}
        self.now = datetime.now(timezone.utc)
        self.policy = create_signed_policy(
            self.identity,
            service_id="web2:lab.test",
            sequence=1,
            issued_at=self.now - timedelta(seconds=1),
            expires_at=self.now + timedelta(minutes=5),
            max_requests=2,
            window_seconds=30,
            max_body_bytes=32,
            origin_id="origin:lab.test",
        )
        self.origin = ThreadingHTTPServer(("127.0.0.1", 0), OriginHandler)
        self.origin.daemon_threads = True
        self.origin_thread = threading.Thread(target=self.origin.serve_forever, daemon=True)
        self.origin_thread.start()
        self.addCleanup(self.origin.shutdown)
        self.addCleanup(self.origin.server_close)
        self.addCleanup(self.origin_thread.join, 2)
        self.intent_now = [100.0]
        self.intent_lobby = CDDIntentLobby(
            {"read-document": IntentRoute(destination_id="web2:docs", content_cid="bafybeigdyrzt5sfp7udm7hu76uh4d3g5q4m3f4j2q")},
            clock=lambda: self.intent_now[0],
        )
        self.config = CDDGatewayConfig(
            origin_url=f"http://127.0.0.1:{self.origin.server_port}",
            service_id="web2:lab.test",
            origin_id="origin:lab.test",
            policy=self.policy,
            trusted_issuer_keys=self.trusted,
            last_sequence=0,
            timeout_seconds=2,
            origin_auth_token=OriginHandler.token,
            intent_lobby=self.intent_lobby,
            intent_destination_paths={"web2:docs": "/intent-document"},
            intent_ttl_seconds=120,
            intent_min_wait_seconds=3,
        )
        self.gateway = create_cdd_server(("127.0.0.1", 0), self.config)
        self.gateway_thread = threading.Thread(target=self.gateway.serve_forever, daemon=True)
        self.gateway_thread.start()
        self.addCleanup(self.gateway.shutdown)
        self.addCleanup(self.gateway.server_close)
        self.addCleanup(self.gateway_thread.join, 2)
        self.base = f"http://127.0.0.1:{self.gateway.server_port}"

    def request(self, path="/ok", *, method="GET", data=None, headers=None):
        req = Request(self.base + path, data=data, headers=headers or {}, method=method)
        try:
            return urlopen(req, timeout=3)
        except urllib.error.HTTPError as exc:
            return exc

    def test_lobby_issues_opaque_ticket_without_exposing_cid(self):
        response = self.request("/_cdd/lobby?intent=read-document")
        self.assertEqual(response.status, 200)
        payload = json.loads(response.read().decode("utf-8"))
        self.assertIn("ticket", payload)
        self.assertEqual(payload["consume_endpoint"], "/_cdd/consume")
        self.assertNotIn("bafy", json.dumps(payload))
        self.assertNotIn("intent-document", json.dumps(payload))

    def test_lobby_rejects_unregistered_intent(self):
        response = self.request("/_cdd/lobby?intent=https%3A%2F%2Fevil.example")
        self.assertEqual(response.status, 400)

    def test_consume_requires_wait_and_routes_only_to_configured_destination(self):
        response = self.request("/_cdd/lobby?intent=read-document")
        ticket = json.loads(response.read().decode("utf-8"))["ticket"]
        body = json.dumps({"ticket": ticket}).encode("utf-8")
        early = self.request("/_cdd/consume", method="POST", data=body, headers={"Content-Type": "application/json"})
        self.assertEqual(early.status, 403)
        self.intent_now[0] += 3
        accepted = self.request("/_cdd/consume", method="POST", data=body, headers={"Content-Type": "application/json"})
        self.assertEqual(accepted.status, 200)
        self.assertEqual(accepted.read(), b"origin:/intent-document")

    def test_consumed_ticket_cannot_be_replayed(self):
        response = self.request("/_cdd/lobby?intent=read-document")
        ticket = json.loads(response.read().decode("utf-8"))["ticket"]
        self.intent_now[0] += 3
        body = json.dumps({"ticket": ticket}).encode("utf-8")
        accepted = self.request("/_cdd/consume", method="POST", data=body, headers={"Content-Type": "application/json"})
        self.assertEqual(accepted.status, 200)
        replay = self.request("/_cdd/consume", method="POST", data=body, headers={"Content-Type": "application/json"})
        self.assertEqual(replay.status, 403)


    def test_gateway_forwards_allowed_request_to_configured_origin(self):
        response = self.request("/page?x=1")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.read(), b"origin:/page?x=1")

    def test_gateway_limits_repeated_requests(self):
        first = self.request("/rate")
        second = self.request("/rate")
        third = self.request("/rate")
        self.assertEqual((first.status, second.status, third.status), (200, 200, 429))
        self.assertEqual(third.read(), b"request rate limit exceeded")

    def test_gateway_rejects_request_body_above_signed_policy_limit(self):
        response = self.request("/upload", method="POST", data=b"x" * 33)
        self.assertEqual(response.status, 413)
        self.assertEqual(response.read(), b"request body too large")

    def test_gateway_does_not_use_client_forwarding_headers_as_identity(self):
        first = self.request("/forwarded", headers={"X-Forwarded-For": "192.0.2.1"})
        second = self.request("/forwarded", headers={"X-Forwarded-For": "198.51.100.8"})
        third = self.request("/forwarded", headers={"X-Forwarded-For": "203.0.113.9"})
        self.assertEqual((first.status, second.status, third.status), (200, 200, 429))

    def test_direct_origin_bypass_is_denied_without_gateway_token(self):
        try:
            response = urlopen(
                f"http://127.0.0.1:{self.origin.server_port}/direct",
                timeout=2,
            )
        except urllib.error.HTTPError as exc:
            response = exc
        self.assertEqual(response.status, 403)
        self.assertEqual(response.read(), b"origin access denied")

    def test_mismatched_origin_policy_fails_before_server_starts(self):
        wrong = CDDGatewayConfig(
            origin_url=self.config.origin_url,
            service_id=self.config.service_id,
            origin_id="origin:other.test",
            policy=self.policy,
            trusted_issuer_keys=self.trusted,
        )
        with self.assertRaises(CDDGatewayError):
            create_cdd_server(("127.0.0.1", 0), wrong)

    def test_kubo_adapter_publishes_and_verifies_exact_signed_policy(self):
        kubo = FakeKubo()
        cid = publish_policy_to_kubo(kubo, self.policy)
        self.assertEqual(cid, kubo.cid)
        self.assertTrue(kubo.pinned)
        loaded = load_policy_from_kubo(kubo, cid, self.trusted, now=self.now)
        self.assertEqual(loaded, self.policy)

    def test_kubo_adapter_rejects_tampered_or_untrusted_policy(self):
        kubo = FakeKubo()
        publish_policy_to_kubo(kubo, self.policy)
        value = json.loads(kubo.payload.decode("utf-8"))
        value["origin_id"] = "origin:attacker.test"
        kubo.payload = json.dumps(value).encode()
        with self.assertRaises(CDDGatewayError):
            load_policy_from_kubo(kubo, kubo.cid, self.trusted, now=self.now)
        with self.assertRaises(CDDGatewayError):
            load_policy_from_kubo(kubo, kubo.cid, {}, now=self.now)


if __name__ == "__main__":
    unittest.main()
