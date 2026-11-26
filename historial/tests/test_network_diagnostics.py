import unittest
from unittest.mock import patch

from node_core.network_diagnostics import collect_network_diagnostics, _read_text


class NetworkDiagnosticsTests(unittest.TestCase):
    def test_collector_returns_expected_sections_without_external_probes(self):
        result = collect_network_diagnostics(probe_external=False)
        self.assertIn("interfaces", result)
        self.assertIn("default_route", result)
        self.assertEqual(result["dns_resolution"]["status"], "NOT_CHECKED")
        self.assertEqual(result["tcp_connectivity"], [])
        self.assertIn("proc_net", result)
        self.assertIn("limitations", result)

    def test_restricted_proc_file_is_reported_as_unavailable(self):
        with patch("pathlib.Path.read_text", side_effect=PermissionError("denied")):
            content, error = _read_text(__import__("pathlib").Path("/proc/net/route"))
        self.assertIsNone(content)
        self.assertIn("PermissionError", error)

    def test_permission_denial_is_not_reported_as_network_failure(self):
        result = collect_network_diagnostics(probe_external=False)
        self.assertTrue(any("may restrict /proc/net" in item for item in result["limitations"]))
        self.assertEqual(result["dns_resolution"]["status"], "NOT_CHECKED")


if __name__ == "__main__":
    unittest.main()
