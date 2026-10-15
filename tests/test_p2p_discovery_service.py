import socket
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.discovery import DiscoveryAnnouncement
from node_core.p2p.discovery_service import (
    DEFAULT_MULTICAST_GROUP,
    DEFAULT_MULTICAST_PORT,
    DiscoveryServiceError,
    NodeDiscoveryService,
)


class FakeDatagramSocket:
    def __init__(self, *args, **kwargs):
        self.closed = False
        self.sent = []
        self.timeout = 0.5

    def setsockopt(self, *args):
        return None

    def bind(self, *args):
        return None

    def settimeout(self, value):
        self.timeout = value

    def sendto(self, payload, destination):
        self.sent.append((payload, destination))
        return len(payload)

    def recvfrom(self, size):
        time.sleep(0.01)
        raise socket.timeout()

    def close(self):
        self.closed = True


class NodeDiscoveryServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.identity = NodeIdentityStore(Path(self.temp.name))
        self.identity.initialize()

    def test_defaults_are_defined_and_valid(self):
        service = NodeDiscoveryService(self.identity, p2p_port=4242)
        self.assertEqual(service.multicast_group, DEFAULT_MULTICAST_GROUP)
        self.assertEqual(service.multicast_port, DEFAULT_MULTICAST_PORT)
        self.assertFalse(service.running)

    def test_rejects_invalid_configuration(self):
        # Port zero means the identity can be discovered before a listener is ready.
        service = NodeDiscoveryService(self.identity, p2p_port=0)
        self.assertFalse(service.running)
        with self.assertRaises(ValueError):
            NodeDiscoveryService(self.identity, p2p_port=-1)
        with self.assertRaises(ValueError):
            NodeDiscoveryService(
                self.identity, p2p_port=4242, multicast_group="192.168.1.1"
            )
        with self.assertRaises(ValueError):
            NodeDiscoveryService(
                self.identity, p2p_port=4242, multicast_port=70000
            )

    def test_snapshot_expires_old_peers(self):
        service = NodeDiscoveryService(
            self.identity, p2p_port=4242, peer_ttl_seconds=1
        )
        peer = DiscoveryAnnouncement(
            node_id="sha256:" + "a" * 64,
            public_key="b" * 64,
            host="192.168.1.20",
            port=4242,
            timestamp=int(time.time()),
        )
        service._peers[peer.node_id] = (peer, time.monotonic() - 2)
        self.assertEqual(service.snapshot(), ())

    def test_start_announces_and_stop_releases_socket(self):
        fake_socket = FakeDatagramSocket()
        with patch(
            "node_core.p2p.discovery_service.socket.socket",
            return_value=fake_socket,
        ):
            service = NodeDiscoveryService(
                self.identity,
                p2p_port=4242,
                interface_ip="192.168.1.10",
                announce_interval_seconds=1,
            )
            service.start()
            deadline = time.monotonic() + 1
            while not fake_socket.sent and time.monotonic() < deadline:
                time.sleep(0.01)
            service.stop()

        self.assertTrue(fake_socket.sent)
        self.assertEqual(
            fake_socket.sent[0][1],
            (DEFAULT_MULTICAST_GROUP, DEFAULT_MULTICAST_PORT),
        )
        self.assertTrue(fake_socket.closed)
        self.assertFalse(service.running)

    def test_rejects_loopback_as_discovery_interface(self):
        service = NodeDiscoveryService(
            self.identity, p2p_port=4242, interface_ip="127.0.0.1"
        )
        with patch("node_core.p2p.discovery_service.socket.socket", return_value=FakeDatagramSocket()):
            with self.assertRaises(DiscoveryServiceError):
                service.start()


if __name__ == "__main__":
    unittest.main()
