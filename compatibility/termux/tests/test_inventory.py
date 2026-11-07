#!/usr/bin/env python3
"""Non-destructive tests for Termux Lobby inventory functions."""
import importlib.util
import unittest
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1] / "lobby" / "server.py"
spec = importlib.util.spec_from_file_location("termux_lobby_server", SERVER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class InventoryTests(unittest.TestCase):
    def test_termux_info_fields(self):
        info = module.termux_info()
        for key in ("platform", "is_termux", "machine", "python", "home"):
            self.assertIn(key, info)

    def test_node_core_detection_states(self):
        result = module.detect_node_core()
        self.assertIn(result["status"], ("installed", "partial_or_residual", "not_installed"))
        self.assertIn("app", result["layout"])

    def test_directory_report_policy(self):
        result = module.directory_report()
        self.assertIn("targets", result)
        self.assertIn("No file contents", result["policy"])

    def test_diagnostics_sections(self):
        result = module.diagnostics()
        for key in ("environment", "node_core", "tools", "packages",
                    "network", "directories", "checks", "summary", "privacy"):
            self.assertIn(key, result)
        self.assertTrue(result["privacy"]["read_only"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
