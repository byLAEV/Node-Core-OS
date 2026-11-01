"""Bounded concurrent hybrid-attack test against a local Node Core OS TLS server.

Synthetic identities only. The HTTPS service binds to 127.0.0.1 and the test does
not contact public hosts, use production credentials, or execute SQL payloads.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
import re
import sqlite3
import sys
import ssl
import tempfile
import threading
import time
import unittest
from pathlib import Path

# pytest may place tests/ first on sys.path; make the repository package explicit.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.tls_transport import NodeTLSTransport, TLSTransportError


REQUESTS_PER_VECTOR = 100
MAX_WORKERS = 50
FLOOD_LIMIT = 25
MAX_BODY_BYTES = 8192
OVERSIZED_BODY_BYTES = 64 * 1024
BASE_PATH = "/api/v1"
SQL_PATTERN = re.compile(
    r"\b(?:DROP\s+TABLE|DELETE\s+FROM|ALTER\s+TABLE|UNION\s+SELECT)\b|--",
    re.IGNORECASE,
)


class _StressState:
    def __init__(self, authorized_node_id: str):
        self.authorized_node_id = authorized_node_id
        self.lock = threading.Lock()
        self.rate_counts: dict[tuple[str, str], int] = {}
        self.db_lock = threading.Lock()
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        with self.db_lock:
            self.db.execute(
                "CREATE TABLE nodes (node_id TEXT PRIMARY KEY, state TEXT NOT NULL)"
            )
            self.db.commit()

    def next_rate_count(self, node_id: str, route: str) -> int:
        with self.lock:
            key = (node_id, route)
            count = self.rate_counts.get(key, 0) + 1
            self.rate_counts[key] = count
            return count

    def close(self):
        with self.db_lock:
            self.db.close()


class _StressHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 256


def _contains_sql_pattern(value) -> bool:
    if isinstance(value, str):
        return bool(SQL_PATTERN.search(value))
    if isinstance(value, dict):
        return any(_contains_sql_pattern(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_sql_pattern(item) for item in value)
    return False


def _handler_for(state: _StressState):
    class StressHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def _reply(self, status: int, payload: dict):
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass
            self.close_connection = True

        def _dispatch(self, method: str):
            try:
                peer = NodeTLSTransport.verify_peer_identity(self.connection)
            except (TLSTransportError, ValueError, ssl.SSLError):
                self._reply(403, {"status": "BLOCKED", "reason": "invalid_tls_identity"})
                return

            claimed_id = self.headers.get("X-Node-ID", "")
            if not claimed_id or claimed_id != peer["node_id"]:
                self._reply(403, {"status": "BLOCKED", "reason": "identity_claim_mismatch"})
                return
            if peer["node_id"] != state.authorized_node_id:
                self._reply(403, {"status": "BLOCKED", "reason": "node_not_authorized"})
                return

            if method == "GET" and self.path == "/health":
                self._reply(200, {"status": "PASS", "service": "node-core-os-web2-stress-lab"})
                return

            if method == "GET" and self.path == BASE_PATH + "/secure-coordination":
                count = state.next_rate_count(peer["node_id"], "GET:/secure-coordination")
                if count > FLOOD_LIMIT:
                    self._reply(429, {"status": "LIMITED", "reason": "local_rate_limit"})
                else:
                    self._reply(200, {"status": "PASS", "request_number": count})
                return

            if method == "POST" and self.path == BASE_PATH + "/secure-coordination":
                self._reply(200, {"status": "PASS"})
                return

            if method == "POST" and self.path == BASE_PATH + "/db-sync":
                length_text = self.headers.get("Content-Length", "")
                if not length_text.isdigit():
                    self._reply(400, {"status": "REJECTED", "reason": "invalid_content_length"})
                    return
                length = int(length_text)
                if length > MAX_BODY_BYTES:
                    self._reply(413, {"status": "REJECTED", "reason": "payload_too_large"})
                    return

                raw = self.rfile.read(length)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._reply(400, {"status": "REJECTED", "reason": "invalid_json"})
                    return
                if not isinstance(payload, dict):
                    self._reply(400, {"status": "REJECTED", "reason": "invalid_schema"})
                    return
                if _contains_sql_pattern(payload):
                    self._reply(400, {"status": "REJECTED", "reason": "unsafe_sql_pattern"})
                    return
                if set(payload) != {"node_id", "state"}:
                    self._reply(400, {"status": "REJECTED", "reason": "invalid_schema"})
                    return
                if payload["node_id"] != peer["node_id"]:
                    self._reply(403, {"status": "BLOCKED", "reason": "payload_identity_mismatch"})
                    return
                if not isinstance(payload["state"], str) or len(payload["state"]) > 256:
                    self._reply(400, {"status": "REJECTED", "reason": "invalid_state"})
                    return

                # Parameterized SQL: request content is never executed as a statement.
                with state.db_lock:
                    state.db.execute(
                        "INSERT OR REPLACE INTO nodes (node_id, state) VALUES (?, ?)",
                        (payload["node_id"], payload["state"]),
                    )
                    state.db.commit()
                self._reply(200, {"status": "PASS", "operation": "parameterized_sync"})
                return

            self._reply(404, {"status": "NOT_FOUND"})

    return StressHandler


class TestWeb2HeavyStress(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="node-core-web2-stress-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)

        self.server_store = NodeIdentityStore(root / "server")
        self.client_store = NodeIdentityStore(root / "authorized-client")
        self.attacker_store = NodeIdentityStore(root / "attacker-client")
        self.server_store.initialize()
        self.client_meta = self.client_store.initialize()
        self.attacker_meta = self.attacker_store.initialize()

        self.server_tls = NodeTLSTransport(self.server_store)
        self.client_tls = NodeTLSTransport(self.client_store)
        self.attacker_tls = NodeTLSTransport(self.attacker_store)
        self.server_cert = self.server_tls.ensure_certificate()
        self.client_cert = self.client_tls.ensure_certificate()
        self.attacker_cert = self.attacker_tls.ensure_certificate()

        self.state = _StressState(self.client_meta["node_id"])
        self.addCleanup(self.state.close)

        self.server = _StressHTTPServer(
            ("127.0.0.1", 0),
            _handler_for(self.state),
        )
        self.server.socket = self.server_tls.server_context(
            [self.client_cert, self.attacker_cert]
        ).wrap_socket(self.server.socket, server_side=True)
        self.port = self.server.server_address[1]
        self.server_thread = threading.Thread(
            target=self.server.serve_forever,
            name="node-core-os-web2-stress-server",
            daemon=True,
        )
        self.server_thread.start()
        self.addCleanup(self._stop_server)

        self.client_context = self.client_tls.client_context([self.server_cert])
        self.attacker_context = self.attacker_tls.client_context([self.server_cert])

    def _stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=3)

    def _send_attack(self, vector: str):
        started = time.perf_counter()
        context = self.attacker_context if vector == "spoofing" else self.client_context
        claimed_id = self.client_meta["node_id"]
        conn = http.client.HTTPSConnection(
            "127.0.0.1", self.port, context=context, timeout=5
        )
        try:
            headers = {"X-Node-ID": claimed_id, "Connection": "close"}
            if vector == "flood":
                conn.request("GET", BASE_PATH + "/secure-coordination", headers=headers)
            elif vector == "spoofing":
                headers["X-Client-Signature"] = "FORGED_HASH"
                headers["Content-Type"] = "application/json"
                conn.request(
                    "POST",
                    BASE_PATH + "/secure-coordination",
                    body=b'{"data":"fake"}',
                    headers=headers,
                )
            elif vector == "injection":
                headers["Content-Type"] = "application/json"
                body = json.dumps({"state_mutation": "DROP TABLE nodes; --"}).encode("utf-8")
                conn.request("POST", BASE_PATH + "/db-sync", body=body, headers=headers)
            elif vector == "oversized":
                headers["Content-Type"] = "application/json"
                body = b'{"data":"' + (b"X" * OVERSIZED_BODY_BYTES) + b'"}'
                # Test early rejection using the declared length. Do not upload
                # a body that the server is designed to reject immediately:
                # the resulting peer close can otherwise look like a transport
                # failure even though the 413 defense worked as intended.
                conn.putrequest("POST", BASE_PATH + "/db-sync")
                for key, value in headers.items():
                    conn.putheader(key, value)
                conn.putheader("Content-Length", str(len(body)))
                conn.endheaders()
            else:
                return {
                    "vector": vector, "status": 0, "duration_seconds": 0.0,
                    "error": "unknown_vector",
                }

            response = conn.getresponse()
            response.read()
            return {
                "vector": vector,
                "status": response.status,
                "duration_seconds": round(time.perf_counter() - started, 6),
                "error": "",
            }
        except (OSError, ssl.SSLError, http.client.HTTPException, TimeoutError) as exc:
            return {
                "vector": vector,
                "status": 0,
                "duration_seconds": round(time.perf_counter() - started, 6),
                "error": type(exc).__name__,
            }
        finally:
            conn.close()

    def _send_health(self):
        conn = http.client.HTTPSConnection(
            "127.0.0.1", self.port, context=self.client_context, timeout=5
        )
        try:
            conn.request("GET", "/health", headers={
                "X-Node-ID": self.client_meta["node_id"],
                "Connection": "close",
            })
            response = conn.getresponse()
            response.read()
            return response.status
        finally:
            conn.close()

    def _send_valid_sync(self):
        conn = http.client.HTTPSConnection(
            "127.0.0.1", self.port, context=self.client_context, timeout=5
        )
        try:
            body = json.dumps({
                "node_id": self.client_meta["node_id"],
                "state": "legitimate-after-stress",
            }).encode("utf-8")
            conn.request(
                "POST",
                BASE_PATH + "/db-sync",
                body=body,
                headers={
                    "X-Node-ID": self.client_meta["node_id"],
                    "Content-Type": "application/json",
                    "Connection": "close",
                },
            )
            response = conn.getresponse()
            response.read()
            return response.status
        finally:
            conn.close()

    def _database_table_exists(self):
        with self.state.db_lock:
            row = self.state.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes'"
            ).fetchone()
            return row is not None

    def test_concurrent_hybrid_attack_and_post_stress_recovery(self):
        vectors = ("flood", "spoofing", "injection", "oversized")
        tasks = [vector for index in range(REQUESTS_PER_VECTOR) for vector in vectors]
        results = []

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(self._send_attack, vector) for vector in tasks]
            for future in as_completed(futures):
                results.append(future.result())
        total_duration = time.perf_counter() - started

        by_vector = {
            vector: [item for item in results if item["vector"] == vector]
            for vector in vectors
        }
        status_counts = {
            vector: {
                str(code): sum(item["status"] == code for item in by_vector[vector])
                for code in (0, 200, 201, 400, 403, 413, 429, 500, 502, 503)
            }
            for vector in vectors
        }
        all_durations = sorted(item["duration_seconds"] for item in results)
        p95_index = max(0, math.ceil(0.95 * len(all_durations)) - 1)
        transport_errors = sum(item["status"] == 0 for item in results)
        server_errors = sum(item["status"] >= 500 for item in results)
        defensive_rejections = sum(
            item["status"] in (400, 403, 413, 429) for item in results
        )
        malicious_successes = sum(
            item["status"] in (200, 201)
            for vector in ("spoofing", "injection", "oversized")
            for item in by_vector[vector]
        )

        health_after_stress = self._send_health()
        valid_sync_after_stress = self._send_valid_sync()
        table_exists_after_stress = self._database_table_exists()

        checks = {
            "all_400_requests_completed": len(results) == 400,
            "no_transport_errors": transport_errors == 0,
            "no_server_5xx_responses": server_errors == 0,
            "flood_rate_limit_applied": status_counts["flood"]["429"] >= 75,
            "identity_spoofing_rejected": status_counts["spoofing"]["403"] == 100,
            "injection_payloads_rejected": status_counts["injection"]["400"] == 100,
            "oversized_payloads_rejected": status_counts["oversized"]["413"] == 100,
            "at_least_90_percent_returned_defensive_status": defensive_rejections >= 360,
            "no_malicious_vector_returned_success": malicious_successes == 0,
            "health_endpoint_works_after_stress": health_after_stress == 200,
            "legitimate_sync_accepted_after_stress": valid_sync_after_stress == 200,
            "database_table_survives_attack": table_exists_after_stress,
        }
        report = {
            "schema_version": 1,
            "report": "Node Core OS byLAEV - Web2 concurrent hybrid stress test",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "environment": {
                "target": "HTTPS service bound only to 127.0.0.1",
                "transport": "Node Core OS TLS 1.3 pinned-certificate mutual TLS",
                "external_hosts_contacted": False,
                "production_credentials_used": False,
                "workers": MAX_WORKERS,
                "requests": len(results),
                "requests_per_vector": REQUESTS_PER_VECTOR,
            },
            "summary": {
                "result": "PASS" if all(checks.values()) else "FAIL",
                "duration_seconds": round(total_duration, 6),
                "requests_per_second": round(len(results) / total_duration, 3) if total_duration else 0,
                "latency_seconds": {
                    "median": all_durations[len(all_durations) // 2] if all_durations else None,
                    "p95": all_durations[p95_index] if all_durations else None,
                    "max": max(all_durations) if all_durations else None,
                },
                "defensive_status_responses": defensive_rejections,
                "defensive_status_rate_percent": round(
                    defensive_rejections * 100 / len(results), 2
                ) if results else 0,
                "transport_errors": transport_errors,
                "server_5xx_responses": server_errors,
                "malicious_vector_successes": malicious_successes,
                "post_stress_health_status": health_after_stress,
                "post_stress_legitimate_sync_status": valid_sync_after_stress,
                "database_table_present_after_stress": table_exists_after_stress,
                "checks": checks,
            },
            "vectors": {
                vector: {
                    "requests": len(by_vector[vector]),
                    "status_counts": status_counts[vector],
                }
                for vector in vectors
            },
            "limitations": [
                "This is a bounded local stress test, not a public-site or volumetric DDoS test.",
                "The database is an in-memory SQLite fixture; production database resilience is not established.",
                "The SQL payload is rejected by this lab input policy and is never executed as SQL.",
                "One post-stress valid request is a recovery/canary check, not a statistical false-positive rate.",
                "The results do not establish that eight proposed certificate profiles are deployable web-server certificates.",
            ],
            "failed_checks": [name for name, passed in checks.items() if not passed],
        }

        artifact_root = Path(os.environ.get("NODE_CORE_TEST_ARTIFACTS_DIR", Path(tempfile.gettempdir()) / "node-core-test-artifacts"))
        output_dir = artifact_root / "web2-heavy-stress"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "web2-heavy-stress-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        lines = [
            "# Node Core OS byLAEV - Web2 concurrent hybrid stress report",
            "",
            "- Generated UTC: " + report["generated_at_utc"],
            "- Result: **" + report["summary"]["result"] + "**",
            "- Target: 127.0.0.1 only; 400 requests; 50 concurrent workers.",
            "- Duration: **" + str(report["summary"]["duration_seconds"]) + " s**",
            "- Throughput: **" + str(report["summary"]["requests_per_second"]) + " requests/s**",
            "- Defensive status responses: **" + str(defensive_rejections) + "/400 (" + str(report["summary"]["defensive_status_rate_percent"]) + "%)**",
            "- Transport errors: **" + str(transport_errors) + "**",
            "- HTTP 5xx responses: **" + str(server_errors) + "**",
            "- Successful responses to spoofing/injection/oversized vectors: **" + str(malicious_successes) + "**",
            "",
            "## Vector outcomes",
            "",
            "| Vector | Requests | 200 | 400 | 403 | 413 | 429 | Transport errors |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for vector in vectors:
            counts = status_counts[vector]
            lines.append(
                "| " + vector + " | " + str(len(by_vector[vector])) + " | " +
                str(counts["200"]) + " | " + str(counts["400"]) + " | " +
                str(counts["403"]) + " | " + str(counts["413"]) + " | " +
                str(counts["429"]) + " | " + str(counts["0"]) + " |"
            )
        lines.extend(["", "## Acceptance checks", ""])
        lines.extend("- [" + ("x" if passed else " ") + "] " + name for name, passed in checks.items())
        lines.extend(["", "## Explicit limitations", ""])
        lines.extend("- " + item for item in report["limitations"])
        lines.extend([
            "",
            "> Passing this lab establishes only these assertions in this isolated environment; it is not a production security certification.",
            "",
        ])
        (output_dir / "web2-heavy-stress-report.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )

        # Report files are preserved by the workflow even if these assertions fail.
        self.assertTrue(
            all(checks.values()),
            "Stress acceptance checks failed: " + ", ".join(report["failed_checks"]),
        )
