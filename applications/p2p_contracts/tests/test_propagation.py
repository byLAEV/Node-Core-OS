import json
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest

from applications.p2p_contracts.p2p_contracts.propagation import (
    MESSAGE_SCHEMA, PropagationProtocol, WINDOW_SECONDS, parse_timestamp, timestamp, utc_now,
)

class FakeStorage:
    def __init__(self, root): self.root = Path(root)
    def path(self, relative): return self.root / relative

class FakeIdentity:
    peer_id = "QmFakeNodeIdentity012345678901234567890123456789"
    addresses = ()

class FakeNetwork:
    def identity(self): return FakeIdentity()

class FakeKubo:
    executable = "ipfs"
    def __init__(self): self.published = []
    def status(self):
        class Status: running = True
        return Status()
    def _environment(self): return {}
    def pubsub_publish(self, topic, encoded):
        if topic != "node-core-os/p2p-contracts/propagation/v1":
            raise RuntimeError("Unexpected PubSub topic.")
        self.published.append(json.loads(encoded))

    def _run(self, *args):
        if args[:2] == ("pubsub", "pub"):
            self.published.append(json.loads(args[3]))
        return type("Result", (), {"stdout": ""})()

class PropagationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.kubo = FakeKubo()
        self.protocol = PropagationProtocol(FakeStorage(temp.name), FakeNetwork(), self.kubo)
        self.protocol.start = lambda: None

    def test_kubo_json_base64_payload_is_decoded_without_stripping_first_character(self):
        import base64
        payload = b'{"type":"TEST"}'
        encoded = base64.b64encode(payload).decode("ascii")
        self.assertEqual(PropagationProtocol._decode_pubsub_data(encoded), payload)
        urlsafe = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        self.assertEqual(PropagationProtocol._decode_pubsub_data(urlsafe), payload)
        multibase = "m" + base64.b64encode(payload).decode("ascii")
        self.assertEqual(PropagationProtocol._decode_pubsub_data(multibase), payload)
        multibase_url = "u" + urlsafe
        self.assertEqual(PropagationProtocol._decode_pubsub_data(multibase_url), payload)

    def test_pending_request_is_accepted_only_for_matching_active_proposal(self):
        from applications.p2p_contracts.p2p_contracts.service import document_hash, REQUEST_SCHEMA
        state = self.protocol.accept_new_propagation("a" * 64)
        payload = {
            "schema": REQUEST_SCHEMA,
            "request_id": "request-12345678-1234-1234-1234-123456789abc",
            "request_type": "btc_exchange",
            "requester": {"node_id": "QmFakeNodeIdentity012345678901234567890123456789"},
        }
        document = {**payload, "document_hash": document_hash(payload)}
        message = {
            "message_id": "test-message", "sender_node_id": "QmFakeNodeIdentity012345678901234567890123456789",
            "proposal_id": state["proposal_id"], "proposal_hash": state["proposal_hash"],
            "request_document": document,
        }
        self.assertEqual(self.protocol._queue_request(message), payload["request_id"])
        self.assertEqual(len(self.protocol._pending_requests), 1)
        self.assertEqual(self.protocol._queue_request(message), payload["request_id"])
        self.assertEqual(len(self.protocol._pending_requests), 1)

    def test_ten_minute_window_is_exact(self):
        self.assertEqual(WINDOW_SECONDS, 600)
        now = utc_now().replace(microsecond=0)
        self.assertEqual(parse_timestamp(timestamp(now + timedelta(minutes=10))), now + timedelta(minutes=10))

    def test_acceptance_persists_and_announces_proposal(self):
        state = self.protocol.accept_new_propagation("a" * 64)
        self.assertEqual(state["status"], "ACCEPTED")
        self.assertEqual(parse_timestamp(state["send_enabled_at"]) - parse_timestamp(state["accepted_at"]), timedelta(minutes=10))
        self.assertEqual(len(self.kubo.published), 2)
        self.assertEqual(self.kubo.published[0]["schema"], MESSAGE_SCHEMA)
        self.assertEqual(self.kubo.published[0]["type"], "PROPOSAL_ANNOUNCE")
        self.assertEqual(self.protocol.current_state()["proposal_hash"], state["proposal_hash"])

    def test_submission_unlocks_after_timestamp(self):
        state = self.protocol.accept_new_propagation(None)
        state["send_enabled_at"] = timestamp(utc_now() - timedelta(seconds=1))
        self.protocol._save_state(state)
        self.assertEqual(self.protocol.current_state()["status"], "READY_TO_SUBMIT")

    def test_expired_lease_is_cancelled_before_enablement(self):
        state = self.protocol.accept_new_propagation(None)
        state["lease_expires_at"] = timestamp(utc_now() - timedelta(seconds=1))
        self.protocol._save_state(state)
        self.assertEqual(self.protocol.current_state()["status"], "CANCELLED")

if __name__ == "__main__":
    unittest.main()
