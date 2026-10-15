import os
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.tls_transport import NodeTLSTransport
from node_core.runtime import NodeRuntime


class NativeP2PRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.previous_data_dir = os.environ.get("NODE_CORE_DATA_DIR")
        self.previous_config = os.environ.get("NODE_CORE_CONFIG")
        os.environ["NODE_CORE_DATA_DIR"] = str(self.root / "runtime-data")
        os.environ.pop("NODE_CORE_CONFIG", None)
        self.addCleanup(self._restore_environment)
        self.runtime = NodeRuntime()
        self.runtime.boot()

    def _restore_environment(self):
        if self.previous_data_dir is None:
            os.environ.pop("NODE_CORE_DATA_DIR", None)
        else:
            os.environ["NODE_CORE_DATA_DIR"] = self.previous_data_dir
        if self.previous_config is None:
            os.environ.pop("NODE_CORE_CONFIG", None)
        else:
            os.environ["NODE_CORE_CONFIG"] = self.previous_config
        self.runtime.shutdown()

    def test_native_status_initializes_identity_without_kubo(self):
        status = self.runtime.native_p2p_status()
        self.assertTrue(status["node_id"].startswith("sha256:"))
        self.assertFalse(status["service_running"])
        self.assertEqual(status["trusted_count"], 0)
        self.assertTrue(Path(status["certificate_path"]).is_file())
        self.assertIn("discovery_running", status)
        self.assertIn("discovery_error", status)
        self.assertIn("discovered_peers", status)
        self.assertIsInstance(status["discovered_peers"], list)


    def test_discovery_can_be_started_without_kubo_or_trusted_peers(self):
        # LAN multicast may be unavailable in CI, so assert graceful startup handling
        # rather than requiring the host network to support multicast.
        result = self.runtime.start_native_discovery()
        status = self.runtime.native_p2p_status()
        self.assertIsInstance(result, bool)
        self.assertEqual(status["trusted_count"], 0)
        self.assertIn("discovery_running", status)
        if not result:
            self.assertTrue(status["discovery_error"])

    def test_discovery_retries_after_initial_failure_and_stops_cleanly(self):
        from node_core.p2p.discovery_service import NodeDiscoveryService

        attempts = {"count": 0}

        class FakeDiscovery:
            running = False

            def __init__(self, *args, **kwargs):
                self.running = False

            def start(self):
                attempts["count"] += 1
                if attempts["count"] == 1:
                    raise OSError("simulated LAN interface not ready")
                self.running = True

            def stop(self):
                self.running = False

            def snapshot(self):
                return ()

        with patch("node_core.p2p.discovery_service.NodeDiscoveryService", FakeDiscovery):
            self.runtime.p2p_discovery = None
            self.runtime._p2p_discovery_retry_thread = None
            self.runtime._p2p_discovery_stop_event.clear()
            self.assertFalse(self.runtime.start_native_discovery())
            self.assertIn("simulated LAN interface not ready", self.runtime._p2p_discovery_error)

            retry = self.runtime._p2p_discovery_retry_thread
            self.assertIsNotNone(retry)
            retry.join(timeout=2.5)
            self.assertFalse(retry.is_alive(), "discovery retry should finish after successful startup")
            self.assertEqual(attempts["count"], 2)
            self.assertTrue(self.runtime.p2p_discovery.running)
            self.assertIsNone(self.runtime._p2p_discovery_error)
            self.runtime.stop_native_discovery()

    def test_listener_requires_an_explicit_trusted_peer(self):
        from node_core.p2p.service import PeerServiceError
        with self.assertRaises(PeerServiceError):
            self.runtime.start_native_p2p()

    def test_trusted_peer_can_be_added_listed_and_revoked(self):
        remote_root = self.root / "remote"
        remote_identity = NodeIdentityStore(remote_root)
        remote_meta = remote_identity.initialize()
        certificate = NodeTLSTransport(remote_identity).ensure_certificate()
        certificate_path = self.root / "remote-cert.pem"
        certificate_path.write_bytes(certificate)

        added = self.runtime.trust_peer_certificate(
            remote_meta["node_id"], certificate_path, "remote-test"
        )
        self.assertEqual(added["node_id"], remote_meta["node_id"])
        self.assertEqual(self.runtime.p2p_trust.get(remote_meta["node_id"])["status"], "trusted")

        revoked = self.runtime.revoke_trusted_peer(remote_meta["node_id"])
        self.assertEqual(revoked["status"], "revoked")
        self.assertEqual(self.runtime.p2p_trust.get(remote_meta["node_id"])["status"], "revoked")

    def test_listener_starts_and_stops_with_trusted_peer(self):
        remote_root = self.root / "remote"
        remote_identity = NodeIdentityStore(remote_root)
        remote_meta = remote_identity.initialize()
        certificate = NodeTLSTransport(remote_identity).ensure_certificate()
        certificate_path = self.root / "remote-cert.pem"
        certificate_path.write_bytes(certificate)
        self.runtime.trust_peer_certificate(remote_meta["node_id"], certificate_path)

        host, port = self.runtime.start_native_p2p()
        self.assertEqual(host, "127.0.0.1")
        self.assertGreater(port, 0)
        self.assertTrue(self.runtime.native_p2p_status()["service_running"])

        self.runtime.stop_native_p2p()
        self.assertFalse(self.runtime.native_p2p_status()["service_running"])


if __name__ == "__main__":
    unittest.main()
