from __future__ import annotations

import os
import socket
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from node_core.web_service import NodeWebServiceManager


class NodeWebServiceManagerTests(unittest.TestCase):
    def test_web_service_refuses_root(self):
        manager = NodeWebServiceManager(Path("/tmp/node-core-test"), Path.cwd())
        with patch("node_core.web_service.os.geteuid", return_value=0):
            with self.assertRaisesRegex(RuntimeError, "user-only"):
                manager.start()

    def test_status_reports_stopped_without_pid_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = NodeWebServiceManager(root / ".node-core", Path.cwd())
            status = manager.status()
            self.assertFalse(status["running"])
            self.assertEqual(status["host"], "127.0.0.1")
            self.assertEqual(status["port"], 8765)

    @unittest.skipIf(getattr(os, "geteuid", lambda: 1)() == 0, "web service E2E must run as non-root")
    def test_start_health_and_stop_real_local_web_api(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / ".node-core"
            data_dir.mkdir()
            app_root = Path(__file__).resolve().parents[1]
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            manager = NodeWebServiceManager(data_dir, app_root)
            with patch.dict(os.environ, {"NODE_CORE_WEB_PORT": str(port)}, clear=False):
                status = manager.start()
                self.assertTrue(status["running"])
                self.assertEqual(status["port"], port)
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/github/binding", timeout=3
                ) as response:
                    self.assertEqual(response.status, 200)
                stopped = manager.stop()
                self.assertFalse(stopped["running"])


if __name__ == "__main__":
    unittest.main()
