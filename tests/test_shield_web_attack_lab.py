"""Node Core OS Shield attack lab: signed-node corroboration + HTTPS controls.

This is a bounded loopback simulation. Three synthetic node identities sign reports;
the test service verifies them locally and applies quarantine/rate limits. It does
not claim to connect to or prove convergence of a live distributed node network.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.tls_transport import NodeTLSTransport
from node_core.security.distributed_defense import (
    create_signed_security_event,
    should_quarantine,
)


class _ShieldState:
    def __init__(self, trusted_reporter_keys, events):
        self.trusted_reporter_keys = trusted_reporter_keys
        self.events = events
        self.rate_limit = 5
        self.request_counts = {}
        self.lock = threading.Lock()


def _handler_for(state):
    class ShieldHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_GET(self):
            try:
                peer = NodeTLSTransport.verify_peer_identity(self.connection)
            except Exception:
                self.send_error(403, "node identity rejected")
                return

            node_id = peer["node_id"]
            if should_quarantine(
                node_id,
                state.events,
                state.trusted_reporter_keys,
                minimum_independent_reporters=3,
            ):
                self._reply(403, {"status": "BLOCKED", "reason": "corroborated_node_alert"})
                return

            with state.lock:
                count = state.request_counts.get(node_id, 0) + 1
                state.request_counts[node_id] = count
            if count > state.rate_limit:
                self._reply(429, {"status": "LIMITED", "reason": "local_rate_limit"})
                return
            self._reply(200, {"status": "PASS", "node_id": node_id})

        def _reply(self, status, payload):
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return ShieldHandler


class ShieldWebAttackLabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)

        self.server_store = NodeIdentityStore(root / "server")
        self.client_store = NodeIdentityStore(root / "client")
        self.attacker_store = NodeIdentityStore(root / "attacker")
        self.reporter_stores = [
            NodeIdentityStore(root / f"reporter-{index}") for index in range(1, 4)
        ]
        self.server_meta = self.server_store.initialize()
        self.client_meta = self.client_store.initialize()
        self.attacker_meta = self.attacker_store.initialize()
        self.reporter_meta = [store.initialize() for store in self.reporter_stores]

        self.server_tls = NodeTLSTransport(self.server_store)
        self.client_tls = NodeTLSTransport(self.client_store)
        self.attacker_tls = NodeTLSTransport(self.attacker_store)
        self.server_cert = self.server_tls.ensure_certificate()
        self.client_cert = self.client_tls.ensure_certificate()
        self.attacker_cert = self.attacker_tls.ensure_certificate()
        self.reporter_keys = {
            meta["node_id"]: meta["public_key"] for meta in self.reporter_meta
        }
        self.events = []
        self.state = _ShieldState(self.reporter_keys, self.events)

        server = ThreadingHTTPServer(("127.0.0.1", 0), _handler_for(self.state))
        server.daemon_threads = True
        server.allow_reuse_address = True
        server.socket = self.server_tls.server_context(
            [self.client_cert, self.attacker_cert]
        ).wrap_socket(server.socket, server_side=True)
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)
        self.thread.start()
        self.port = server.server_address[1]
        self.addCleanup(self._stop_server)

    def _stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def _get(self, store, tls):
        cert = self.client_cert if store is self.client_store else self.attacker_cert
        conn = http.client.HTTPSConnection(
            "127.0.0.1",
            self.port,
            context=tls.client_context([self.server_cert]),
            timeout=3,
        )
        try:
            conn.request("GET", "/")
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, payload
        finally:
            conn.close()

    def _report_attack(self, subject_id):
        now = datetime.now(timezone.utc)
        digest = hashlib.sha256(
            f"synthetic attack observation:{subject_id}".encode("utf-8")
        ).hexdigest()
        for store in self.reporter_stores:
            self.events.append(
                create_signed_security_event(
                    store,
                    event_type="web_abuse_observed",
                    subject_id=subject_id,
                    observed_at=now,
                    expires_at=now + timedelta(minutes=5),
                    evidence_sha256=digest,
                    confidence="corroborated",
                )
            )

    def test_legitimate_node_can_reach_protected_web_service(self):
        status, payload = self._get(self.client_store, self.client_tls)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["node_id"], self.client_meta["node_id"])

    def test_one_or_two_reports_do_not_trigger_quarantine(self):
        now = datetime.now(timezone.utc)
        digest = hashlib.sha256(b"bounded synthetic evidence").hexdigest()
        for store in self.reporter_stores[:2]:
            self.events.append(
                create_signed_security_event(
                    store,
                    event_type="web_abuse_observed",
                    subject_id=self.attacker_meta["node_id"],
                    observed_at=now,
                    expires_at=now + timedelta(minutes=5),
                    evidence_sha256=digest,
                    confidence="corroborated",
                )
            )
        status, payload = self._get(self.attacker_store, self.attacker_tls)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "PASS")

    def test_three_trusted_signed_reports_quarantine_attacker_node(self):
        self._report_attack(self.attacker_meta["node_id"])
        status, payload = self._get(self.attacker_store, self.attacker_tls)
        self.assertEqual(status, 403)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertEqual(payload["reason"], "corroborated_node_alert")

    def test_tampered_report_does_not_quarantine(self):
        self._report_attack(self.attacker_meta["node_id"])
        self.events[0]["subject_id"] = self.client_meta["node_id"]
        status, payload = self._get(self.attacker_store, self.attacker_tls)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "PASS")

    def test_local_rate_limit_bounds_repeated_requests(self):
        statuses = [
            self._get(self.client_store, self.client_tls)[0]
            for _ in range(self.state.rate_limit + 2)
        ]
        self.assertEqual(statuses[:5], [200] * 5)
        self.assertEqual(statuses[5:], [429, 429])


if __name__ == "__main__":
    unittest.main()
