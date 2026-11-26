import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "node_core_os", "--help"],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Node Core OS", result.stdout)\n        self.assertIn("user-only", result.stdout)

    def test_status_is_read_only(self):
        with tempfile.TemporaryDirectory() as home:
            env = {
                **os.environ,
                "HOME": home,
                "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
            }
            result = subprocess.run(
                [sys.executable, "-m", "node_core_os", "status"],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.strip(), "status command returned empty output")\n            payload = json.loads(result.stdout)
            self.assertFalse(payload["initialized"])
            self.assertFalse((Path(home) / ".local/share/node-core-os").exists())


if __name__ == "__main__":
    unittest.main()
