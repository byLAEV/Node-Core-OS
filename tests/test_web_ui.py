"""Tests for the read-only local web interface."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from node_core.ipfs import KuboStatus
from node_core.web_ui import _kubo_status, _port_from_environment


class WebInterfaceTests(unittest.TestCase):
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
