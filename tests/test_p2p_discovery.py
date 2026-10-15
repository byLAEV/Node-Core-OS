import json
import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.discovery import (
    DiscoveryAnnouncementError,
    create_announcement,
    parse_announcement,
)


class DiscoveryAnnouncementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.identity = NodeIdentityStore(Path(self.temp.name))
        self.identity.initialize()

    def test_signed_announcement_round_trips(self):
        payload = create_announcement(
            self.identity, "192.168.1.10", 4242, timestamp=1000
        )
        announcement = parse_announcement(payload, now=1000)
        self.assertEqual(announcement.node_id, self.identity.load()["node_id"])
        self.assertEqual(announcement.host, "192.168.1.10")
        self.assertEqual(announcement.port, 4242)

    def test_rejects_tampered_announcement(self):
        payload = create_announcement(
            self.identity, "192.168.1.10", 4242, timestamp=1000
        )
        message = json.loads(payload)
        message["port"] = 4243
        with self.assertRaises(DiscoveryAnnouncementError):
            parse_announcement(json.dumps(message).encode("ascii"), now=1000)

    def test_rejects_expired_announcement(self):
        payload = create_announcement(
            self.identity, "192.168.1.10", 4242, timestamp=1000
        )
        with self.assertRaises(DiscoveryAnnouncementError):
            parse_announcement(payload, now=1061, max_age_seconds=60)

    def test_rejects_wrong_node_id(self):
        payload = create_announcement(
            self.identity, "192.168.1.10", 4242, timestamp=1000
        )
        message = json.loads(payload)
        message["node_id"] = "sha256:" + "0" * 64
        with self.assertRaises(DiscoveryAnnouncementError):
            parse_announcement(json.dumps(message).encode("ascii"), now=1000)

    def test_rejects_invalid_address_and_port(self):
        with self.assertRaises(DiscoveryAnnouncementError):
            create_announcement(self.identity, "localhost", 4242, timestamp=1000)
        with self.assertRaises(DiscoveryAnnouncementError):
            create_announcement(self.identity, "192.168.1.10", 0, timestamp=1000)


if __name__ == "__main__":
    unittest.main()
