import json
import tempfile
import unittest
from pathlib import Path

from node_core.p2p.message_store import P2PMessageStore, P2PMessageStoreError


def node_id(character):
    return "sha256:" + character * 64


class P2PMessageStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = P2PMessageStore(Path(self.temp.name))
        self.sender = node_id("a")
        self.recipient = node_id("b")
        self.sent_at = "2026-10-23T22:00:00+00:00"

    def receive(self, **overrides):
        values = {
            "from_node_id": self.sender,
            "recipient_node_id": self.recipient,
            "local_node_id": self.recipient,
            "request_id": "request-001",
            "text": "Hola, nodo.",
            "sent_at": self.sent_at,
        }
        values.update(overrides)
        return self.store.record_incoming(**values)

    def test_message_is_saved_as_pending_and_survives_reload(self):
        result = self.receive()
        self.assertEqual(result["status"], "received")
        self.assertEqual(len(self.store.list_inbox()), 1)
        record = P2PMessageStore(Path(self.temp.name)).list_inbox()[0]
        self.assertEqual(record["from_node_id"], self.sender)
        self.assertEqual(record["to_node_id"], self.recipient)
        self.assertEqual(record["text"], "Hola, nodo.")
        self.assertEqual(record["status"], "pending")
        self.assertEqual(json.loads(self.store.path.read_text())["schema_version"], 1)

    def test_wrong_recipient_is_rejected(self):
        with self.assertRaises(P2PMessageStoreError):
            self.receive(recipient_node_id=node_id("c"))
        self.assertEqual(self.store.list_inbox(), [])

    def test_duplicate_request_is_idempotent(self):
        first = self.receive()
        second = self.receive()
        self.assertEqual(first, second)
        self.assertEqual(len(self.store.list_inbox()), 1)

    def test_reusing_request_id_with_changed_text_is_rejected(self):
        self.receive()
        with self.assertRaises(P2PMessageStoreError):
            self.receive(text="altered")
        self.assertEqual(len(self.store.list_inbox()), 1)

    def test_message_size_and_timestamp_are_validated(self):
        with self.assertRaises(P2PMessageStoreError):
            self.receive(text=" " * 3)
        with self.assertRaises(P2PMessageStoreError):
            self.receive(text="x" * 4097)
        with self.assertRaises(P2PMessageStoreError):
            self.receive(sent_at="yesterday")

    def test_mark_read_changes_status(self):
        result = self.receive()
        self.assertTrue(self.store.mark_read(result["message_id"]))
        self.assertEqual(self.store.list_inbox()[0]["status"], "read")
        self.assertFalse(self.store.mark_read("missing"))

    def test_outbox_is_written_after_receipt(self):
        result = self.store.record_outgoing(
            to_node_id=self.recipient,
            request_id="request-002",
            message_id="message-002",
            text="sent",
            sent_at=self.sent_at,
            received_at=self.sent_at,
        )
        self.assertEqual(result["status"], "received")
        self.assertEqual(self.store.list_outbox()[0]["to_node_id"], self.recipient)


if __name__ == "__main__":
    unittest.main()
