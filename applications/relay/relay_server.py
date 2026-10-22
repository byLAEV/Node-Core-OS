"""Minimal durable HTTP relay for authenticated Node Core OS test manifests.

Run only behind a TLS reverse proxy on a trusted host. This server binds to
127.0.0.1 by default; it does not itself provide TLS or public hosting.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from node_core.relay_delivery import canonical_json_bytes, decode_key

RUN_ID = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


class RelayState:
    def __init__(self, database: Path, key_hex: str) -> None:
        self.database = database
        self.key = decode_key(key_hex)
        database.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS deliveries (
                run_id TEXT PRIMARY KEY,
                payload_json BLOB NOT NULL,
                payload_sha256 TEXT NOT NULL,
                request_hmac TEXT NOT NULL,
                receipt_json BLOB,
                created_at INTEGER NOT NULL
            )""")

    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def auth(self, value: object) -> bool:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            return False
        # Authenticate HTTP API requests with HMAC(method + newline + path + newline + body).
        return True

    def request_signature(self, method: str, path: str, body: bytes) -> str:
        message = method.encode() + b"\n" + path.encode() + b"\n" + body
        return hmac.new(self.key, message, hashlib.sha256).hexdigest()

    def verify_http(self, method: str, path: str, body: bytes, signature: str) -> bool:
        expected = self.request_signature(method, path, body)
        return hmac.compare_digest(expected, signature)

    def enqueue(self, envelope: dict) -> dict:
        from node_core.relay_delivery import verify_request
        verified = verify_request(envelope, self.key.hex())
        payload_json = canonical_json_bytes(verified["payload"])
        with self.lock, self.connect() as db:
            existing = db.execute(
                "SELECT payload_sha256, receipt_json FROM deliveries WHERE run_id=?",
                (verified["run_id"],),
            ).fetchone()
            if existing:
                if existing[0] != verified["payload_sha256"]:
                    raise ValueError("run_id already exists with different payload.")
                return {"status": "queued", "run_id": verified["run_id"], "duplicate": True}
            db.execute(
                "INSERT INTO deliveries(run_id,payload_json,payload_sha256,request_hmac,created_at) VALUES(?,?,?,?,?)",
                (verified["run_id"], payload_json, verified["payload_sha256"],
                 envelope["hmac_sha256"], int(time.time())),
            )
        return {"status": "queued", "run_id": verified["run_id"], "duplicate": False}

    def take_next(self) -> dict | None:
        with self.lock, self.connect() as db:
            row = db.execute(
                "SELECT run_id,payload_json,payload_sha256,request_hmac FROM deliveries WHERE receipt_json IS NULL ORDER BY created_at LIMIT 1"
            ).fetchone()
            if not row:
                return None
            run_id, payload_json, digest, request_hmac = row
            return {
                "schema": "node-core-os/relay-delivery/v1",
                "run_id": run_id,
                "payload": json.loads(payload_json),
                "payload_sha256": digest,
                "hmac_sha256": request_hmac,
            }

    def save_receipt(self, receipt: dict) -> None:
        run_id = receipt.get("run_id")
        if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
            raise ValueError("Invalid receipt run_id.")
        encoded = canonical_json_bytes(receipt)
        with self.lock, self.connect() as db:
            row = db.execute(
                "SELECT payload_sha256, receipt_json FROM deliveries WHERE run_id=?", (run_id,)
            ).fetchone()
            if row is None:
                raise ValueError("No queued delivery for this run_id.")
            if receipt.get("payload_sha256") != row[0] or receipt.get("status") != "persisted":
                raise ValueError("Receipt does not acknowledge the queued payload.")
            if row[1] is not None and bytes(row[1]) != encoded:
                raise ValueError("Conflicting receipt already stored.")
            db.execute("UPDATE deliveries SET receipt_json=? WHERE run_id=?", (encoded, run_id))

    def get_receipt(self, run_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT receipt_json FROM deliveries WHERE run_id=?", (run_id,)).fetchone()
        return json.loads(row[0]) if row and row[0] else None


class Handler(BaseHTTPRequestHandler):
    server_version = "NodeCoreRelay/1"

    def log_message(self, format, *args):
        # Avoid logging payloads, signatures, or credentials.
        print("relay", self.command, self.path.split("?")[0], args[1] if len(args) > 1 else "")

    def _body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 1024 * 1024:
            raise ValueError("Body must be between 1 byte and 1 MiB.")
        return self.rfile.read(length)

    def _send(self, status: int, value: dict):
        body = canonical_json_bytes(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self, body: bytes) -> bool:
        path = urlparse(self.path).path
        sig = self.headers.get("X-Node-Core-Auth", "")
        return self.server.state.verify_http(self.command, path, body, sig)

    def do_POST(self):
        try:
            body = self._body()
            if not self._authorized(body):
                self._send(401, {"error": "authentication_failed"})
                return
            path = urlparse(self.path).path
            value = json.loads(body)
            if path == "/v1/manifest":
                result = self.server.state.enqueue(value)
            elif path == "/v1/receipt":
                self.server.state.save_receipt(value)
                result = {"status": "accepted", "run_id": value["run_id"]}
            else:
                self._send(404, {"error": "not_found"})
                return
            self._send(200, result)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)[:200]})

    def do_GET(self):
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        try:
            if path == "/health":
                self._send(200, {"status": "ok"})
                return
            body = b""
            if not self._authorized(body):
                self._send(401, {"error": "authentication_failed"})
                return
            if path == "/v1/next":
                result = self.server.state.take_next() or {"status": "empty"}
            elif path == "/v1/receipt":
                run_id = query.get("run_id", [""])[0]
                if not RUN_ID.fullmatch(run_id):
                    self._send(400, {"error": "invalid_run_id"})
                    return
                result = self.server.state.get_receipt(run_id) or {"status": "pending", "run_id": run_id}
            else:
                self._send(404, {"error": "not_found"})
                return
            self._send(200, result)
        except (ValueError, TypeError, KeyError) as exc:
            self._send(400, {"error": str(exc)[:200]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("NODE_CORE_RELAY_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("NODE_CORE_RELAY_PORT", "8765")))
    parser.add_argument("--database", type=Path, default=Path(os.environ.get("NODE_CORE_RELAY_DB", "./relay.sqlite3")))
    args = parser.parse_args()
    key = os.environ.get("NODE_CORE_RELAY_HMAC_KEY", "")
    state = RelayState(args.database, key)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.state = state
    print(f"Relay listening on {args.host}:{args.port}; place behind TLS reverse proxy.")
    server.serve_forever()


if __name__ == "__main__":
    main()
