import json
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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

class FakeService:
    def __init__(self):
        self.import_calls = 0
        self.manifest = {"manifest_hash": "manifest-hash-1", "sequence": 1}

    def import_remote_requests(self, documents):
        self.import_calls += 1
        return {
            "imported_count": len(documents),
            "manifest_hash": self.manifest["manifest_hash"],
            "manifest_sequence": self.manifest["sequence"],
            "manifest_document": self.manifest,
        }

    def current_manifest(self):
        return self.manifest


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

    def test_cli_publish_retries_transient_validation_ignored_with_same_message(self):
        class CliOnlyKubo:
            executable = "ipfs"
            def _environment(self):
                return {}

        self.protocol.kubo = CliOnlyKubo()
        failure = __import__("subprocess").CalledProcessError(
            1,
            ["ipfs", "pubsub", "pub", "topic", "-"],
            stderr="Error: validation ignored",
        )
        success = type("Result", (), {"stdout": "", "stderr": ""})()
        with patch(
            "applications.p2p_contracts.p2p_contracts.propagation.subprocess.run",
            side_effect=[failure, success],
        ) as run, patch(
            "applications.p2p_contracts.p2p_contracts.propagation.time.sleep"
        ) as sleep:
            message = self.protocol._publish("STATUS_QUERY", test_field="same-payload")

        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].kwargs["input"], run.call_args_list[1].kwargs["input"])
        encoded = json.loads(run.call_args_list[0].kwargs["input"])
        self.assertEqual(encoded["message_id"], message["message_id"])
        self.assertEqual(encoded["test_field"], "same-payload")
        sleep.assert_called_once_with(0.25)

    def test_cli_publish_stops_after_three_validation_ignored_failures(self):
        import subprocess

        class CliOnlyKubo:
            executable = "ipfs"
            def _environment(self):
                return {}

        self.protocol.kubo = CliOnlyKubo()
        failure = subprocess.CalledProcessError(
            1,
            ["ipfs", "pubsub", "pub", "topic", "-"],
            stderr="Error: validation ignored",
        )
        with patch(
            "applications.p2p_contracts.p2p_contracts.propagation.subprocess.run",
            side_effect=[failure, failure, failure],
        ) as run, patch(
            "applications.p2p_contracts.p2p_contracts.propagation.time.sleep"
        ):
            with self.assertRaisesRegex(RuntimeError, "after 3 attempt"):
                self.protocol._publish("STATUS_QUERY")

        self.assertEqual(run.call_count, 3)

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

    def test_missing_batch_ack_keeps_exact_manifest_retryable(self):
        remote_peer = "QmRemoteNodeIdentity012345678901234567890123456789"
        service = FakeService()
        self.protocol.service = service
        state = self.protocol.accept_new_propagation(None, require_owner_request=True)
        state["send_enabled_at"] = timestamp(utc_now() - timedelta(seconds=1))
        state["status"] = "READY_TO_SUBMIT"
        self.protocol._save_state(state)
        pending_document = {"request_id": "request-test-pending"}
        self.protocol._pending_requests = [pending_document]
        self.protocol._save_pending()
        self.protocol._received.append({
            "type": "PROPOSAL_STATUS",
            "proposal_id": state["proposal_id"],
            "sender_node_id": remote_peer,
        })

        clock = {"value": 0.0}
        def mocked_sleep(seconds):
            clock["value"] += seconds

        # Advance simulated time only when the protocol sleeps. This keeps deadline
        # checks deterministic and allows an ACK appended during publish to be read.
        with patch("applications.p2p_contracts.p2p_contracts.propagation.time.monotonic",
                   side_effect=lambda: clock["value"]), \
             patch("applications.p2p_contracts.p2p_contracts.propagation.time.sleep",
                   side_effect=mocked_sleep):
            first = self.protocol.finalize_propagation()

        self.assertEqual(first["missing_peer_ids"], [remote_peer])
        self.assertFalse(first["batch_flushed"])
        saved_after_first = self.protocol._state()
        self.assertEqual(saved_after_first["status"], "PENDING_ACKS")
        self.assertFalse(saved_after_first["batch_flushed"])
        self.assertEqual(self.protocol._pending_requests, [pending_document])
        self.assertEqual(saved_after_first["final_manifest_document"], service.manifest)
        self.assertEqual(service.import_calls, 1)

        # An ACK retry must still be possible after the proposal lease expires:
        # the exact manifest and batch are already committed and persisted.
        saved_after_first["lease_expires_at"] = timestamp(utc_now() - timedelta(seconds=1))
        self.protocol._save_state(saved_after_first)

        original_publish = self.protocol._publish
        def publish_with_ack(kind, **fields):
            message = original_publish(kind, **fields)
            if kind == "REQUEST_BATCH":
                self.protocol._received.append({
                    "type": "BATCH_ACK",
                    "reply_to": message["message_id"],
                    "sender_node_id": remote_peer,
                    "manifest_hash": service.manifest["manifest_hash"],
                })
            return message
        self.protocol._publish = publish_with_ack

        with patch("applications.p2p_contracts.p2p_contracts.propagation.time.monotonic",
                   side_effect=lambda: clock["value"]), \
             patch("applications.p2p_contracts.p2p_contracts.propagation.time.sleep",
                   side_effect=mocked_sleep):
            second = self.protocol.finalize_propagation()

        self.assertEqual(second["missing_peer_ids"], [])
        self.assertTrue(second["batch_flushed"])
        self.assertEqual(self.protocol._state()["status"], "FINALIZED")
        self.assertEqual(self.protocol._pending_requests, [])
        self.assertEqual(service.import_calls, 1, "Retry must reuse the saved manifest, not create another one.")

    def test_listener_stdout_closed_during_shutdown_does_not_raise(self):
        class ClosedStdout:
            def __iter__(self):
                raise ValueError("I/O operation on closed file")

        class StoppedListener:
            stdout = ClosedStdout()
            def poll(self):
                return 0

        self.protocol._listener = StoppedListener()
        self.protocol._read_loop()
        self.assertEqual(self.protocol._listener_errors, [])

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
