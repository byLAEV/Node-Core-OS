import json
from datetime import timedelta
import tempfile
from pathlib import Path
import unittest
from applications.p2p_contracts.p2p_contracts.propagation import (
    MESSAGE_SCHEMA, KuboPubSub, PropagationProtocol, WINDOW_SECONDS,
    parse_timestamp, timestamp, utc_now,
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
    def __init__(self): self.published = []
    def status(self):
        class Status: running = True
        return Status()
    def _environment(self): return {}
    def _run(self, *args):
        if args[:2] == ("pubsub", "pub"): self.published.append(json.loads(args[3]))
        return type("Result", (), {"stdout": ""})()
    def _rpc_json(self, *args, **kwargs): return {"ID": FakeIdentity.peer_id}
class PropagationProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.kubo = FakeKubo()
        self.protocol = PropagationProtocol(FakeStorage(self.temp.name), FakeNetwork(), self.kubo)
    def test_message_schema_requires_node_identity(self):
        with self.assertRaises(ValueError):
            KuboPubSub._validate_message({"schema": MESSAGE_SCHEMA, "message_id": "id", "type": "STATUS_QUERY"})
    def test_ten_minute_window_is_exact(self):
        self.assertEqual(WINDOW_SECONDS, 600)
        now = utc_now().replace(microsecond=0)
        self.assertEqual(parse_timestamp(timestamp(now + timedelta(seconds=600))), now + timedelta(seconds=600))
    def test_accept_creates_hash_and_announces(self):
        state = self.protocol.accept_new_propagation("a" * 64)
        self.assertEqual(state["status"], "ACCEPTED")
        self.assertEqual(state["window_seconds"], 600)
        self.assertEqual(parse_timestamp(state["send_enabled_at"]) - parse_timestamp(state["accepted_at"]), timedelta(minutes=10))
        self.assertEqual(len(self.kubo.published), 2)
        self.assertEqual(self.kubo.published[0]["type"], "PROPOSAL_ANNOUNCE")
    def test_current_state_enables_after_deadline(self):
        state = self.protocol.accept_new_propagation(None)
        state["send_enabled_at"] = timestamp(utc_now() - timedelta(seconds=1))
        self.protocol._save_state(state)
        self.assertEqual(self.protocol.current_state()["status"], "READY_TO_SUBMIT")
    def test_query_status_without_responses_is_not_verified(self):
        self.protocol.start = lambda: None
        self.protocol._publish = lambda *args, **kwargs: {"message_id": "query"}
        result = self.protocol.query_status(wait_seconds=0.5)
        self.assertEqual(result["status"], "NO_NODE_RESPONSES")
if __name__ == "__main__": unittest.main()
