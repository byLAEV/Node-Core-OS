import json
import tempfile
import unittest
from pathlib import Path

from node_core.identity_presence import IdentityPresence, PROTOCOL, REPORT_PROTOCOL


class FakeNetwork:
    def identity(self):
        return type("Identity", (), {"peer_id": "QmLocalNodeId12345678901234567890"})()

    def connected_peers(self):
        return ("QmPeerNodeId12345678901234567890",)


class FakeProfile:
    def __init__(self, node_id=None):
        self.node_id = node_id

    def load(self):
        return {"node_id": self.node_id} if self.node_id else None


class FakeKubo:
    def __init__(self):
        self.objects = {}
        self.pinned = set()

    def add_file(self, path, pin=False):
        data = Path(path).read_bytes()
        cid = "bafy" + str(abs(hash(data)))
        self.objects[cid] = data
        if pin:
            self.pinned.add(cid)
        return type("Added", (), {"cid": cid})()

    def cat(self, cid):
        return self.objects[cid]

    def pin_add(self, cid):
        self.pinned.add(cid)

    def pin_list(self):
        return {cid: {"Type": "recursive"} for cid in self.pinned}


class IdentityPresenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kubo = FakeKubo()
        self.network = FakeNetwork()
        self.profile = FakeProfile(self.network.identity().peer_id)
        self.service = IdentityPresence(self.root, self.profile, self.network, self.kubo)

    def tearDown(self):
        self.temp.cleanup()

    def test_announcement_contains_only_public_node_id_and_boolean_claim(self):
        announcement = self.service.announce()
        self.assertEqual(announcement["protocol"], PROTOCOL)
        self.assertEqual(announcement["node_id"], self.network.identity().peer_id)
        self.assertTrue(announcement["identity_associated"])
        saved = list((self.root / "identity-presence" / "announcements").glob("*.json"))
        self.assertEqual(len(saved), 1)
        text = saved[0].read_text(encoding="utf-8")
        self.assertNotIn("document_number", text)
        self.assertNotIn("full_name", text)

    def test_association_is_false_when_profile_not_associated_to_current_node(self):
        service = IdentityPresence(self.root, FakeProfile("different-node"), self.network, self.kubo)
        self.assertFalse(service.announce()["identity_associated"])

    def test_import_announcement_by_cid(self):
        announcement = self.service.announce()
        path = self.root / "fixture.json"
        path.write_text(json.dumps(announcement), encoding="utf-8")
        cid = self.kubo.add_file(path).cid
        imported = self.service.import_announcement(cid)
        self.assertEqual(imported["node_id"], announcement["node_id"])

    def test_report_deduplicates_nodes_and_publishes_pinned_report(self):
        self.service.announce()
        incoming = {
            "protocol": PROTOCOL,
            "message_type": "identity_association",
            "node_id": "QmOtherNodeId12345678901234567890",
            "identity_associated": True,
            "claim_status": "announced_not_verified",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        target = self.root / "identity-presence" / "incoming" / "other.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(incoming), encoding="utf-8")
        report = self.service.create_report()
        self.assertEqual(report["protocol"], REPORT_PROTOCOL)
        self.assertEqual(report["known_nodes"], 2)
        self.assertEqual(report["identity_associations_announced"], 2)
        result = self.service.publish_report()
        self.assertTrue(result["pinned_locally"])
        self.assertIn(result["report_cid"], self.kubo.pin_list())

    def test_import_report_rejects_personal_fields_in_announcements(self):
        self.service.announce()
        report = self.service.create_report()
        report["announcements"][0]["full_name"] = "Must Not Be Accepted"
        path = self.root / "unsafe-report.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        cid = self.kubo.add_file(path).cid
        other = IdentityPresence(self.root / "other-node", self.profile, self.network, self.kubo)
        with self.assertRaisesRegex(Exception, "unsupported fields"):
            other.import_report(cid)

    def test_failed_pin_preserves_existing_current_report(self):
        self.service.announce()
        self.service.create_report()
        original_bytes = self.service.current_report_path.read_bytes()

        incoming_report = json.loads(original_bytes.decode("utf-8"))
        incoming_report["report_reference_id"] = "e4f6c77a-4b5f-4e54-bf1a-2d7dbff6c111"
        fixture = self.root / "incoming-report.json"
        fixture.write_text(json.dumps(incoming_report), encoding="utf-8")
        cid = self.kubo.add_file(fixture).cid

        class FailingPinKubo(FakeKubo):
            def __init__(self, source):
                self.objects = source.objects
                self.pinned = set()

            def pin_add(self, cid):
                raise RuntimeError("simulated pin failure")

        self.service.kubo = FailingPinKubo(self.kubo)
        with self.assertRaisesRegex(Exception, "current local report was preserved"):
            self.service.import_report(cid)
        self.assertEqual(self.service.current_report_path.read_bytes(), original_bytes)

    def test_import_report_saves_and_pins_same_bytes(self):
        self.service.announce()
        self.service.create_report()
        published = self.service.publish_report()
        raw = self.kubo.cat(published["report_cid"])
        other_root = self.root / "other-node"
        other = IdentityPresence(other_root, self.profile, self.network, self.kubo)
        state = other.import_report(published["report_cid"])
        self.assertTrue(state["pinned_locally"])
        self.assertEqual(other.current_report_path.read_bytes(), raw)
        self.assertEqual(state["report_cid"], published["report_cid"])


if __name__ == "__main__":
    unittest.main()
