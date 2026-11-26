"""Bounded loopback API abuse tests; no external targets or load generation."""
import http.client
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _LimitedHandler(BaseHTTPRequestHandler):
    max_body = 1024
    request_count = 0
    lock = threading.Lock()

    def do_POST(self):
        with self.lock:
            type(self).request_count += 1
            count = type(self).request_count
        length_text = self.headers.get("Content-Length", "")
        if not length_text.isdigit():
            self.send_error(400, "invalid content length")
            return
        length = int(length_text)
        if length > self.max_body:
            self.send_error(413, "payload too large")
            return
        if count > 5:
            self.send_error(429, "test rate limit")
            return
        body = self.rfile.read(length)
        try:
            json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_error(400, "invalid JSON")
            return
        response = b'{"accepted":true}'
        self.send_response(200)
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, fmt, *args):
        pass


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class BoundedAPIAbuseTests(unittest.TestCase):
    def setUp(self):
        _LimitedHandler.request_count = 0
        self.server = _Server(("127.0.0.1", 0), _LimitedHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def _post(self, body):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=2)
        try:
            conn.request("POST", "/events", body=body, headers={"Content-Type":"application/json"})
            response = conn.getresponse()
            response.read()
            return response.status
        finally:
            conn.close()

    def test_valid_small_json_is_accepted(self):
        self.assertEqual(self._post(b'{"event":"test"}'), 200)

    def test_malformed_json_is_rejected(self):
        self.assertEqual(self._post(b'{broken'), 400)

    def test_oversized_body_is_rejected(self):
        self.assertEqual(self._post(b'{"x":"' + b'a' * 1100 + b'"}'), 413)

    def test_bounded_request_rate_is_enforced(self):
        statuses = [self._post(b'{"n":1}') for _ in range(6)]
        self.assertEqual(statuses[:5], [200] * 5)
        self.assertEqual(statuses[5], 429)


if __name__ == "__main__":
    unittest.main()
