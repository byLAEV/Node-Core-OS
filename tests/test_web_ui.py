"""Tests for the read-only local web interface."""
from __future__ import annotations

import http.client
import json
import os
import threading
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from node_core.ipfs import KuboStatus
from node_core.web_ui import NodeCoreWebServer, _kubo_status, _port_from_environment, _require_unprivileged_user


class WebInterfaceTests(unittest.TestCase):
    def test_root_execution_is_rejected(self) -> None:
        with patch("node_core.web_ui.os.geteuid", return_value=0):
            with self.assertRaisesRegex(SystemExit, "Refusing to run.*as root"):
                _require_unprivileged_user()

    def test_unprivileged_execution_is_allowed(self) -> None:
        with patch("node_core.web_ui.os.geteuid", return_value=10000):
            _require_unprivileged_user()

    def test_default_port_is_8765(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_port_from_environment(), 8765)

    def test_port_whitespace_is_accepted_by_integer_parser(self) -> None:
        with patch.dict(os.environ, {"NODE_CORE_WEB_PORT": " 8766 "}, clear=True):
            self.assertEqual(_port_from_environment(), 8766)

    def test_explicit_port_is_validated(self) -> None:
        with patch.dict(os.environ, {"NODE_CORE_WEB_PORT": "8766"}, clear=True):
            self.assertEqual(_port_from_environment(), 8766)

    def test_invalid_port_is_rejected(self) -> None:
        for value in ("abc", "0", "65536", "-1"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"NODE_CORE_WEB_PORT": value}, clear=True):
                    with self.assertRaises(ValueError):
                        _port_from_environment()

    def test_http_status_endpoint_and_assets(self) -> None:
        runtime = SimpleNamespace(
            kubo=SimpleNamespace(
                status=lambda: KuboStatus(
                    installed=True, initialized=True, running=True,
                    peer_id="12D3KooWExample", version="0.30.0",
                )
            ),
            config=SimpleNamespace(
                ipfs_api="http://127.0.0.1:5001",
                ipfs_repo_path="/tmp/node-core/ipfs",
            ),
        )
        server = NodeCoreWebServer(0, runtime)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_port
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            connection.request("GET", "/api/status", headers={"Host": f"127.0.0.1:{port}"})
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["web_port"], port)
            self.assertEqual(payload["kubo"]["state"], "running")
            connection.close()

            for path, expected_type in (
                ("/", "text/html; charset=utf-8"),
                ("/style.css", "text/css; charset=utf-8"),
                ("/app.js", "text/javascript; charset=utf-8"),
            ):
                with self.subTest(path=path):
                    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
                    connection.request("GET", path, headers={"Host": f"127.0.0.1:{port}"})
                    response = connection.getresponse()
                    body = response.read()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.getheader("Content-Type"), expected_type)
                    self.assertTrue(body)
                    connection.close()

            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            connection.request("POST", "/api/status", body=b"{}", headers={"Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}", "Content-Type": "application/json"})
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 405)
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_http_start_kubo_requires_explicit_confirmation(self) -> None:
        runtime = SimpleNamespace(
            kubo=SimpleNamespace(
                status=lambda: KuboStatus(installed=True, initialized=True, running=False),
                start=lambda: self.fail("Kubo must not start without confirmation"),
            ),
            config=SimpleNamespace(ipfs_api="http://127.0.0.1:5001", ipfs_repo_path="/tmp/node-core/ipfs"),
        )
        server = NodeCoreWebServer(0, runtime)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_port
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            connection.request(
                "POST", "/api/kubo/start", body=b'{"confirm":false}',
                headers={"Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}", "Content-Type": "application/json"},
            )
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 400)
            self.assertIn("confirmation", payload["error"].lower())
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_http_start_kubo_calls_manager_and_verifies_running(self) -> None:
        statuses = [
            KuboStatus(installed=True, initialized=True, running=False),
            KuboStatus(installed=True, initialized=True, running=True, peer_id="12D3KooWExample", version="0.30.0"),
            KuboStatus(installed=True, initialized=True, running=True, peer_id="12D3KooWExample", version="0.30.0"),
        ]
        start_calls = []
        def status():
            return statuses.pop(0) if statuses else KuboStatus(installed=True, initialized=True, running=True, peer_id="12D3KooWExample", version="0.30.0")
        def start():
            start_calls.append(True)
        runtime = SimpleNamespace(
            kubo=SimpleNamespace(status=status, start=start),
            config=SimpleNamespace(ipfs_api="http://127.0.0.1:5001", ipfs_repo_path="/tmp/node-core/ipfs"),
        )
        server = NodeCoreWebServer(0, runtime)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_port
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            connection.request(
                "POST", "/api/kubo/start", body=b'{"confirm":true}',
                headers={"Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}", "Content-Type": "application/json"},
            )
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["message"], "Kubo started successfully.")
            self.assertTrue(payload["kubo"]["running"])
            self.assertEqual(start_calls, [True])
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_http_start_kubo_rejects_untrusted_origin(self) -> None:
        start_calls = []
        runtime = SimpleNamespace(
            kubo=SimpleNamespace(
                status=lambda: KuboStatus(installed=True, initialized=True, running=False),
                start=lambda: start_calls.append(True),
            ),
            config=SimpleNamespace(ipfs_api="http://127.0.0.1:5001", ipfs_repo_path="/tmp/node-core/ipfs"),
        )
        server = NodeCoreWebServer(0, runtime)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_port
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            connection.request(
                "POST", "/api/kubo/start", body=b'{"confirm":true}',
                headers={"Host": f"127.0.0.1:{port}", "Origin": "http://example.invalid", "Content-Type": "application/json"},
            )
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            response.read()
            self.assertEqual(start_calls, [])
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_http_kubo_network_endpoint_reports_direct_peers(self) -> None:
        network_status = SimpleNamespace(
            identity=SimpleNamespace(peer_id="12D3KooWExample"),
            connected_peers=("12D3KooWPeerA", "12D3KooWPeerB"),
        )
        runtime = SimpleNamespace(
            kubo=SimpleNamespace(
                status=lambda: KuboStatus(installed=True, initialized=True, running=True, peer_id="12D3KooWExample", version="0.30.0")
            ),
            network=SimpleNamespace(status=lambda: network_status),
            config=SimpleNamespace(ipfs_api="http://127.0.0.1:5001", ipfs_repo_path="/tmp/node-core/ipfs"),
        )
        server = NodeCoreWebServer(0, runtime)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            connection.request("GET", "/api/network/kubo", headers={"Host": f"127.0.0.1:{server.server_port}"})
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["peer_id"], "12D3KooWExample")
            self.assertEqual(payload["peer_count"], 2)
            self.assertEqual(payload["connected_peers"], ["12D3KooWPeerA", "12D3KooWPeerB"])
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_http_kubo_network_endpoint_does_not_query_peers_when_stopped(self) -> None:
        def unexpected_status():
            raise AssertionError("network status must not be queried while Kubo is stopped")
        runtime = SimpleNamespace(
            kubo=SimpleNamespace(status=lambda: KuboStatus(installed=True, initialized=True, running=False)),
            network=SimpleNamespace(status=unexpected_status),
            config=SimpleNamespace(ipfs_api="http://127.0.0.1:5001", ipfs_repo_path="/tmp/node-core/ipfs"),
        )
        server = NodeCoreWebServer(0, runtime)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            connection.request("GET", "/api/network/kubo", headers={"Host": f"127.0.0.1:{server.server_port}"})
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertFalse(payload["kubo_running"])
            self.assertEqual(payload["peer_count"], 0)
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_kubo_status_reports_actual_running_state(self) -> None:
        runtime = SimpleNamespace(
            kubo=SimpleNamespace(
                status=lambda: KuboStatus(
                    installed=True,
                    initialized=True,
                    running=True,
                    peer_id="12D3KooWExample",
                    version="0.30.0",
                )
            ),
            config=SimpleNamespace(
                ipfs_api="http://127.0.0.1:5001",
                ipfs_repo_path="/tmp/node-core/ipfs",
            ),
        )
        result = _kubo_status(runtime)
        self.assertEqual(result["state"], "running")
        self.assertTrue(result["installed"])
        self.assertTrue(result["initialized"])
        self.assertTrue(result["running"])
        self.assertEqual(result["peer_id"], "12D3KooWExample")
        self.assertEqual(result["version"], "0.30.0")
        self.assertEqual(result["api"], "http://127.0.0.1:5001")
        self.assertEqual(result["repo_path"], "/tmp/node-core/ipfs")

    def test_kubo_api_not_responding_is_not_reported_as_running(self) -> None:
        runtime = SimpleNamespace(
            kubo=SimpleNamespace(
                status=lambda: KuboStatus(
                    installed=True, initialized=True, running=False
                )
            ),
            config=SimpleNamespace(
                ipfs_api="http://127.0.0.1:5001",
                ipfs_repo_path="/tmp/node-core/ipfs",
            ),
        )
        result = _kubo_status(runtime)
        self.assertEqual(result["state"], "not_responding")
        self.assertFalse(result["running"])


if __name__ == "__main__":
    unittest.main()
