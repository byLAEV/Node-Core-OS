"""Three-node TLS Shield alert acceptance tests.

Uses independent node identities and real loopback TLS sockets. Topology is A -> B -> C;
alerts are signed by distinct reporter identities and verified independently at each hop.
This is a controlled integration test, not a production deployment or Internet attack test.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import socket
import socketserver
import tempfile
import threading
import time
import unittest

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.tls_transport import NodeTLSTransport
from node_core.security.distributed_defense import (
    create_signed_security_event,
    should_quarantine,
    verify_signed_security_event,
)


def _read_json_line(sock):
    chunks = []
    while True:
        chunk = sock.recv(1)
        if not chunk:
            break
        if chunk == b"\n":
            break
        chunks.append(chunk)
        if len(chunks) > 1024 * 1024:
            raise ValueError("message exceeds 1 MiB")
    if not chunks:
        raise ConnectionError("peer closed without a response")
    return json.loads(b"".join(chunks).decode("utf-8"))


def _send_tls(node, peer, payload, timeout=2.0):
    context = node["transport"].client_context([peer["cert"]])
    with socket.create_connection(peer["address"], timeout=timeout) as raw:
        with context.wrap_socket(raw, server_hostname=None) as tls:
            actual = NodeTLSTransport.verify_peer_identity(tls, peer["meta"]["node_id"])
            if actual["node_id"] != peer["meta"]["node_id"]:
                raise AssertionError("TLS peer identity mismatch")
            tls.sendall(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode() + b"\n")
            return _read_json_line(tls)


class _NodeTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class ShieldDistributedAlertAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.now = datetime.now(timezone.utc)
        self.nodes = {}
        for label in ("A", "B", "C"):
            store = NodeIdentityStore(root / f"node-{label}")
            meta = store.initialize()
            transport = NodeTLSTransport(store)
            cert = transport.ensure_certificate()
            self.nodes[label] = {
                "label": label, "store": store, "meta": meta,
                "transport": transport, "cert": cert, "events": {},
                "seen": set(), "accepted": 0, "rejected": 0,
                "quarantined": set(), "forward_enabled": True,
                "forward_ms": [], "revoked": set(),
            }
        self.reporters = []
        self.trusted = {}
        for index in range(3):
            store = NodeIdentityStore(root / f"reporter-{index}")
            meta = store.initialize()
            self.reporters.append((store, meta))
            self.trusted[meta["node_id"]] = meta["public_key"]
        self.subject = self.nodes["C"]["meta"]["node_id"]
        self.nodes["A"]["peer"] = self.nodes["B"]
        self.nodes["B"]["peer"] = self.nodes["C"]
        self.nodes["C"]["peer"] = None

        for label in ("A", "B", "C"):
            node = self.nodes[label]
            expected_peer = node["meta"]["node_id"]
            peer_certs = [other["cert"] for other in self.nodes.values()]
            server = _NodeTCPServer(("127.0.0.1", 0), self._handler_for(node, expected_peer))
            server.socket = node["transport"].server_context(peer_certs).wrap_socket(
                server.socket, server_side=True
            )
            node["server"] = server
            node["address"] = server.server_address
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            node["thread"] = thread
            node["peer"] = self.nodes["B"] if label == "A" else (self.nodes["C"] if label == "B" else None)
        self.addCleanup(self._stop_servers)

    def _stop_servers(self):
        for node in self.nodes.values():
            server = node.get("server")
            if server:
                server.shutdown()
                server.server_close()
        for node in self.nodes.values():
            thread = node.get("thread")
            if thread:
                thread.join(timeout=2)

    def _handler_for(self, node, _expected_id):
        outer = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                tls = self.request
                try:
                    peer = NodeTLSTransport.verify_peer_identity(tls)
                    allowed = {
                        "A": {outer.nodes["B"]["meta"]["node_id"]},
                        "B": {outer.nodes["A"]["meta"]["node_id"]},
                        "C": {outer.nodes["B"]["meta"]["node_id"]},
                    }[node["label"]]
                    if peer["node_id"] not in allowed:
                        node["rejected"] += 1
                        tls.sendall(b'{"accepted":false,"reason":"topology_peer_rejected"}\n')
                        return
                    message = _read_json_line(tls)
                    if message.get("schema") != "NODE_CORE_OS_SHIELD_ALERT_TEST_V1":
                        node["rejected"] += 1
                        tls.sendall(b'{"accepted":false,"reason":"bad_schema"}\n')
                        return
                    event = message.get("event")
                    if not isinstance(event, dict):
                        node["rejected"] += 1
                        tls.sendall(b'{"accepted":false,"reason":"missing_event"}\n')
                        return
                    reporter_id = event.get("reporter_node_id")
                    if reporter_id in node["revoked"] or not verify_signed_security_event(
                        event, outer.trusted, now=outer.now
                    ):
                        node["rejected"] += 1
                        tls.sendall(b'{"accepted":false,"reason":"event_untrusted_or_revoked"}\n')
                        return
                    event_id = hashlib.sha256(
                        json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
                    ).hexdigest()
                    if event_id in node["seen"]:
                        node["rejected"] += 1
                        tls.sendall(b'{"accepted":false,"reason":"replay"}\n')
                        return
                    node["seen"].add(event_id)
                    node["events"][event_id] = event
                    node["accepted"] += 1
                    if should_quarantine(
                        outer.subject, list(node["events"].values()), outer.trusted,
                        minimum_independent_reporters=3, now=outer.now,
                    ):
                        node["quarantined"].add(outer.subject)
                    if node["label"] == "B" and node["forward_enabled"]:
                        started = time.monotonic()
                        result = _send_tls(
                            node, outer.nodes["C"],
                            {"schema": "NODE_CORE_OS_SHIELD_ALERT_TEST_V1", "event": event},
                        )
                        node["forward_ms"].append((time.monotonic() - started) * 1000)
                        if not result.get("accepted"):
                            node["rejected"] += 1
                    tls.sendall(json.dumps({
                        "accepted": True, "node": node["label"],
                        "quarantined": outer.subject in node["quarantined"],
                        "valid_reporters": len({
                            e["reporter_node_id"] for e in node["events"].values()
                        }),
                    }, sort_keys=True).encode() + b"\n")
                except Exception as exc:
                    try:
                        node["rejected"] += 1
                        tls.sendall(json.dumps({
                            "accepted": False, "reason": type(exc).__name__
                        }).encode() + b"\n")
                    except OSError:
                        pass
        return Handler

    def _event(self, index, *, expired=False):
        store, _ = self.reporters[index]
        observed = self.now - timedelta(minutes=10) if expired else self.now - timedelta(seconds=1)
        expires = self.now - timedelta(minutes=5) if expired else self.now + timedelta(minutes=5)
        return create_signed_security_event(
            store, event_type="web_abuse_observed", subject_id=self.subject,
            observed_at=observed, expires_at=expires,
            evidence_sha256=hashlib.sha256(f"synthetic-evidence-{index}".encode()).hexdigest(),
            confidence="corroborated",
        )

    def _route(self, event, *, start="A"):
        first = self.nodes[start]
        peer = first["peer"]
        if peer is None:
            raise AssertionError("No next hop configured")
        return _send_tls(first, peer, {
            "schema": "NODE_CORE_OS_SHIELD_ALERT_TEST_V1", "event": event
        })

    def test_alert_propagates_a_to_b_to_c_and_quorum_triggers_only_at_three(self):
        timings = []
        for index in range(3):
            started = time.monotonic()
            response = self._route(self._event(index))
            timings.append((time.monotonic() - started) * 1000)
            self.assertTrue(response["accepted"])
            if index < 2:
                self.assertNotIn(self.subject, self.nodes["C"]["quarantined"])
            else:
                self.assertIn(self.subject, self.nodes["C"]["quarantined"])
        # C receives events via B. Three reporters are required before quarantine.
        self.assertEqual(len(self.nodes["C"]["events"]), 3)
        self.assertIn(self.subject, self.nodes["C"]["quarantined"])
        self.assertEqual(len({e["reporter_node_id"] for e in self.nodes["C"]["events"].values()}), 3)
        self.assertTrue(all(value > 0 for value in timings))
        self.propagation_report = {
            "event_count": 3,
            "latency_ms_per_alert": [round(value, 3) for value in timings],
            "mean_latency_ms": round(sum(timings) / len(timings), 3),
            "max_latency_ms": round(max(timings), 3),
            "node_c_quarantined_after_quorum": True,
        }
        print("SHIELD_DISTRIBUTED_ALERT_REPORT=" + json.dumps(self.propagation_report, sort_keys=True))

    def test_replay_is_rejected(self):
        event = self._event(0)
        first = self._route(event)
        self.assertTrue(first["accepted"])
        second = self._route(event)
        self.assertFalse(second["accepted"])
        self.assertEqual(second["reason"], "replay")

    def test_expired_or_tampered_event_is_rejected(self):
        expired = self._route(self._event(0, expired=True))
        self.assertFalse(expired["accepted"])
        altered = self._event(1)
        altered["subject_id"] = "sha256:" + "0" * 64
        forged = self._route(altered)
        self.assertFalse(forged["accepted"])

    def test_revoked_reporter_is_rejected(self):
        event = self._event(0)
        self.nodes["B"]["revoked"].add(event["reporter_node_id"])
        response = self._route(event)
        self.assertFalse(response["accepted"])

    def test_partition_does_not_create_quorum_and_recovery_converges(self):
        self.nodes["B"]["forward_enabled"] = False
        for index in range(2):
            response = self._route(self._event(index))
            self.assertTrue(response["accepted"])
        self.assertEqual(len(self.nodes["C"]["events"]), 0)
        self.assertNotIn(self.subject, self.nodes["C"]["quarantined"])
        self.nodes["B"]["forward_enabled"] = True
        response = self._route(self._event(2))
        self.assertTrue(response["accepted"])
        self.assertEqual(len(self.nodes["C"]["events"]), 1)
        self.assertNotIn(self.subject, self.nodes["C"]["quarantined"])
        # B retained signed observations while forwarding was partitioned.
        # On reconnection, it forwards the queued observations to C; duplicate event 2 is rejected.
        for event in list(self.nodes["B"]["events"].values()):
            try:
                _send_tls(self.nodes["B"], self.nodes["C"], {
                    "schema": "NODE_CORE_OS_SHIELD_ALERT_TEST_V1", "event": event
                })
            except (ConnectionError, OSError):
                self.fail("Queued event did not reach C after reconnection")
        self.assertEqual(len(self.nodes["C"]["events"]), 3)
        self.assertIn(self.subject, self.nodes["C"]["quarantined"])

    def test_one_or_two_reporters_do_not_quarantine(self):
        for index in range(2):
            self._route(self._event(index))
        self.assertNotIn(self.subject, self.nodes["C"]["quarantined"])
        self.assertEqual(len(self.nodes["C"]["events"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
