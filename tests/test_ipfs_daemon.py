"""Tests for launching Kubo independently from the interactive terminal."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from node_core.ipfs import KuboError, KuboManager, KuboStatus


class KuboBackgroundLaunchTests(unittest.TestCase):
    def test_cli_command_uses_bounded_timeout(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temporary:
            manager = KuboManager("ipfs", Path(temporary) / "ipfs", "http://127.0.0.1:5001")
            with (
                patch.object(manager, "is_installed", return_value=True),
                patch.object(manager, "_environment", return_value={}),
                patch("node_core.ipfs.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run,
            ):
                manager._run("version")
            self.assertEqual(run.call_args.kwargs["timeout"], 60.0)

    def test_cli_timeout_is_reported_as_kubo_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager = KuboManager("ipfs", Path(temporary) / "ipfs", "http://127.0.0.1:5001")
            with (
                patch.object(manager, "is_installed", return_value=True),
                patch.object(manager, "_environment", return_value={}),
                patch(
                    "node_core.ipfs.subprocess.run",
                    side_effect=subprocess.TimeoutExpired(cmd=["ipfs", "version"], timeout=2),
                ),
            ):
                with self.assertRaisesRegex(KuboError, "timed out after 2 seconds"):
                    manager._run("version", timeout=2)

    def test_cli_timeout_must_be_positive(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager = KuboManager("ipfs", Path(temporary) / "ipfs", "http://127.0.0.1:5001")
            with self.assertRaisesRegex(ValueError, "greater than zero"):
                manager._run("version", timeout=0)
    def test_daemon_command_enables_pubsub_flag_when_kubo_advertises_it(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temporary:
            manager = KuboManager("ipfs", Path(temporary) / "ipfs", "http://127.0.0.1:5001")
            with patch("node_core.ipfs.subprocess.run", return_value=SimpleNamespace(
                stdout="Options: --enable-pubsub-experiment", returncode=0
            )):
                self.assertEqual(manager._daemon_command(), ["ipfs", "daemon", "--enable-pubsub-experiment"])

    def test_daemon_command_keeps_default_when_kubo_does_not_advertise_flag(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temporary:
            manager = KuboManager("ipfs", Path(temporary) / "ipfs", "http://127.0.0.1:5001")
            with patch("node_core.ipfs.subprocess.run", return_value=SimpleNamespace(
                stdout="Kubo daemon help", returncode=0
            )):
                self.assertEqual(manager._daemon_command(), ["ipfs", "daemon"])

    def test_start_detaches_daemon_and_redirects_terminal_streams(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "ipfs"
            manager = KuboManager("ipfs", repo, "http://127.0.0.1:5001")

            process = unittest.mock.Mock()
            process.pid = 4321
            process.poll.return_value = None

            with (
                patch.object(manager, "status", side_effect=[
                    KuboStatus(True, True, False),
                    KuboStatus(True, True, True, peer_id="peer-test"),
                ]),
                patch.object(manager, "is_initialized", return_value=True),
                patch.object(manager, "_daemon_command", return_value=["ipfs", "daemon"]),
                patch("node_core.ipfs.subprocess.Popen", return_value=process) as popen,
            ):
                manager.start(wait_seconds=0.5)

            args, kwargs = popen.call_args
            self.assertEqual(args[0], ["ipfs", "daemon"])
            self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
            self.assertIs(kwargs["stderr"], subprocess.STDOUT)
            self.assertTrue(kwargs["start_new_session"])
            self.assertTrue(kwargs["close_fds"])
            self.assertEqual(kwargs["env"]["IPFS_PATH"], str(repo))
            self.assertEqual(manager.pid_path.read_text(encoding="utf-8").strip(), "4321")
            self.assertTrue(manager.log_path.is_file())


if __name__ == "__main__":
    unittest.main()
