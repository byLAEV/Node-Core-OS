import json
import os
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from node_core.evidence import EvidenceManager

from node_core.config import NodeConfig
from node_core.content import ContentManager
from node_core.ipfs import AddedContent, KuboManager
from node_core.storage import StorageManager
from node_core.runtime import NodeRuntime


class FakeKubo:
    def __init__(self):
        self.pinned = set()

    def add_file(self, path, pin=False):
        if pin:
            self.pinned.add("bafytestcid")
        return AddedContent("bafytestcid", path.name, path.stat().st_size)

    def cat(self, cid):
        if cid != "bafytestcid":
            raise ValueError("bad cid")
        return b"node-core"

    def pin_add(self, cid):
        if cid != "bafytestcid":
            raise ValueError("bad cid")
        self.pinned.add(cid)

    def pin_remove(self, cid):
        if cid != "bafytestcid":
            raise ValueError("bad cid")
        self.pinned.discard(cid)

    def pin_list(self):
        return {
            cid: {"Name": "test.txt", "Type": "recursive"}
            for cid in self.pinned
        }


class RuntimeTests(unittest.TestCase):

    def test_boot_starts_installed_kubo_by_default_without_root(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            root = Path(directory)
            config = NodeConfig(
                data_dir=root,
                local_storage_path=root / "storage",
                ipfs_repo_path=root / "ipfs",
            )
            with patch("node_core.runtime.NodeConfig.load", return_value=config):
                runtime = NodeRuntime()
            runtime.storage.initialize = Mock()
            runtime.config.save = Mock()
            runtime.kubo.is_installed = Mock(return_value=True)
            runtime.kubo.start = Mock()
            runtime.start_native_discovery = Mock(return_value=True)
            runtime._start_native_p2p_automation = Mock()

            runtime.boot()

            runtime.kubo.start.assert_called_once_with()
            self.assertIsNone(runtime._kubo_start_error)
            runtime.start_native_discovery.assert_called_once_with()
            runtime._start_native_p2p_automation.assert_called_once_with()

    def test_boot_does_not_fail_when_kubo_auto_start_fails(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            root = Path(directory)
            config = NodeConfig(
                data_dir=root,
                local_storage_path=root / "storage",
                ipfs_repo_path=root / "ipfs",
            )
            with patch("node_core.runtime.NodeConfig.load", return_value=config):
                runtime = NodeRuntime()
            runtime.storage.initialize = Mock()
            runtime.config.save = Mock()
            runtime.kubo.is_installed = Mock(return_value=True)
            runtime.kubo.start = Mock(side_effect=RuntimeError("daemon unavailable"))
            runtime.start_native_discovery = Mock(return_value=True)
            runtime._start_native_p2p_automation = Mock()

            runtime.boot()

            self.assertEqual(runtime._kubo_start_error, "daemon unavailable")
            runtime.start_native_discovery.assert_called_once_with()

    def test_storage_stays_inside_root(self):
        with self.subTest():
            from tempfile import TemporaryDirectory
            with TemporaryDirectory() as directory:
                storage = StorageManager(__import__("pathlib").Path(directory))
                storage.initialize()
                self.assertEqual(
                    storage.path("example.txt").parent,
                    __import__("pathlib").Path(directory),
                )

    def test_config_persists_kubo_settings(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config = NodeConfig(
                data_dir=root,
                local_storage_path=root / "storage",
                ipfs_repo_path=root / "ipfs",
            )
            config.save()
            previous = os.environ.get("NODE_CORE_CONFIG")
            os.environ["NODE_CORE_CONFIG"] = str(config.config_path)
            try:
                loaded = NodeConfig.load()
            finally:
                if previous is None:
                    os.environ.pop("NODE_CORE_CONFIG", None)
                else:
                    os.environ["NODE_CORE_CONFIG"] = previous
            self.assertEqual(loaded.ipfs_repo_path, root / "ipfs")
            stored = json.loads(config.config_path.read_text(encoding="utf-8"))
            self.assertEqual(stored["ipfs_profile"], "unixfs-v1-2025")
            self.assertIs(stored["auto_start_kubo"], True)
            self.assertIs(loaded.auto_start_kubo, True)

    def test_kubo_status_without_binary(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        with TemporaryDirectory() as directory:
            manager = KuboManager(
                executable="definitely-not-installed-node-core-kubo",
                repo_path=Path(directory) / "ipfs",
                api="http://127.0.0.1:5001",
            )
            status = manager.status()
            self.assertFalse(status.installed)
            self.assertFalse(status.running)

    def test_create_text_evidence_stores_local_and_ipfs(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            root = Path(directory)
            storage = StorageManager(root / "storage")
            storage.initialize()
            manager = ContentManager(
                FakeKubo(),
                storage,
                gateway="http://127.0.0.1:8080",
            )

            result = EvidenceManager(manager).create_text("My first evidence.")

            local_path = Path(result.path)
            self.assertTrue(local_path.is_file())
            self.assertEqual(local_path.suffix, ".txt")
            self.assertEqual(
                local_path.read_text(encoding="utf-8"),
                "My first evidence.",
            )
            self.assertEqual(result.content.cid, "bafytestcid")
            self.assertTrue(result.content.pinned)
            self.assertEqual(result.content.source_path, str(local_path.resolve()))

    def test_create_text_evidence_rejects_empty_text(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            root = Path(directory)
            storage = StorageManager(root / "storage")
            storage.initialize()
            manager = ContentManager(FakeKubo(), storage)

            with self.assertRaises(ValueError):
                EvidenceManager(manager).create_text("   ")

    def test_content_end_to_end_with_fake_kubo(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.txt"
            source.write_bytes(b"node-core")
            manager = ContentManager(
                FakeKubo(),
                StorageManager(root / "storage"),
                gateway="http://127.0.0.1:8080",
            )

            result = manager.add(source)
            self.assertEqual(result.cid, "bafytestcid")
            self.assertFalse(result.pinned)
            self.assertEqual(result.source_path, str(source.resolve()))

            destination = root / "out.txt"
            manager.retrieve(result.cid, destination)
            self.assertEqual(destination.read_bytes(), b"node-core")

            published = manager.publish(result.cid)
            self.assertTrue(published.pinned)
            self.assertIsNotNone(published.published_at)
            self.assertEqual(published.publication_mode, "cid")

            reference = manager.share(result.cid)
            self.assertEqual(reference.ipfs_uri, "ipfs://bafytestcid")
            self.assertEqual(
                reference.gateway_url,
                "http://127.0.0.1:8080/ipfs/bafytestcid",
            )

            manager.unpin(result.cid)
            self.assertFalse(manager.get(result.cid).pinned)
            manager.unpublish(result.cid)
            self.assertIsNone(manager.get(result.cid).published_at)

    def test_refresh_network_status_retries_discovery_and_returns_live_status(self):
        runtime = NodeRuntime.__new__(NodeRuntime)
        kubo_status = SimpleNamespace(
            installed=True, initialized=True, running=True,
            peer_id="QmTestPeer", version="0.42.0", detail=None
        )
        native_status = {"discovery_running": True, "wan_discovery_running": False}
        calls = []
        runtime.start_native_discovery = lambda: calls.append("discovery") or True
        runtime._start_native_p2p_automation = lambda: calls.append("automation")
        runtime.kubo = SimpleNamespace(
            status=lambda: kubo_status,
            _run=lambda *args: SimpleNamespace(stdout="/dnsaddr/bootstrap.example/p2p/QmExample\n"),
        )
        runtime.network = SimpleNamespace(connected_peers=lambda: ("QmRemotePeer",))
        runtime.native_p2p_status = lambda: native_status
        runtime._p2p_peer_monitor_error = None

        result = runtime.refresh_network_status()

        self.assertEqual(calls, ["discovery", "automation"])
        self.assertIs(result["kubo"], kubo_status)
        self.assertIs(result["native_p2p"], native_status)
        self.assertEqual(result["kubo_connected_peers"], ["QmRemotePeer"])
        self.assertEqual(result["kubo_bootstrap_peers"], ["/dnsaddr/bootstrap.example/p2p/QmExample"])
        self.assertEqual(result["errors"], [])

    def test_refresh_network_status_reports_discovery_failure_without_claiming_wan(self):
        runtime = NodeRuntime.__new__(NodeRuntime)
        runtime._p2p_discovery_error = "multicast unavailable"
        runtime.start_native_discovery = lambda: False
        runtime._start_native_p2p_automation = lambda: None
        runtime.kubo = SimpleNamespace(status=lambda: None)
        runtime.network = SimpleNamespace(connected_peers=lambda: ())
        runtime.native_p2p_status = lambda: {"wan_discovery_running": False}
        runtime._p2p_peer_monitor_error = None

        result = runtime.refresh_network_status()

        self.assertIn("LAN discovery: multicast unavailable", result["errors"])
        self.assertFalse(result["native_p2p"]["wan_discovery_running"])


if __name__ == "__main__":
    unittest.main()
