import socket
import unittest

from node_core.p2p.session import (
    PeerSessionError,
    receive_application_message,
    send_application_message,
    validate_application_message,
)


class P2PApplicationProtocolTests(unittest.TestCase):
    def test_status_request_round_trips_over_framed_socket(self):
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        message = {
            "version": 1,
            "type": "STATUS",
            "action": "request",
            "request_id": "status-test-1",
        }
        send_application_message(left, message)
        self.assertEqual(receive_application_message(right), message)

    def test_status_response_requires_valid_state_and_timestamp(self):
        message = {
            "version": 1,
            "type": "STATUS",
            "action": "response",
            "request_id": "status-test-2",
            "state": "running",
            "observed_at": "2026-10-15T05:00:00Z",
        }
        self.assertEqual(validate_application_message(message), message)

        message["state"] = "online-ish"
        with self.assertRaises(PeerSessionError):
            validate_application_message(message)

    def test_peers_response_is_bounded_and_validated(self):
        node_id = "sha256:" + "a" * 64
        message = {
            "version": 1,
            "type": "PEERS",
            "action": "response",
            "request_id": "peers-test-1",
            "peers": [node_id],
        }
        self.assertEqual(validate_application_message(message), message)

        message["peers"] = ["not-a-node-id"]
        with self.assertRaises(PeerSessionError):
            validate_application_message(message)

        message["peers"] = [node_id] * 101
        with self.assertRaises(PeerSessionError):
            validate_application_message(message)

        message["peers"] = [node_id, node_id]
        with self.assertRaisesRegex(PeerSessionError, "duplicate"):
            validate_application_message(message)

    def test_peers_request_requires_request_id_and_no_peer_list(self):
        message = {
            "version": 1,
            "type": "PEERS",
            "action": "request",
            "request_id": "peers-test-2",
        }
        self.assertEqual(validate_application_message(message), message)

        message["peers"] = []
        with self.assertRaisesRegex(PeerSessionError, "must not include"):
            validate_application_message(message)

        del message["peers"]
        message["request_id"] = ""
        with self.assertRaises(PeerSessionError):
            validate_application_message(message)

    def test_unknown_type_and_version_are_rejected(self):
        with self.assertRaises(PeerSessionError):
            validate_application_message({"version": 1, "type": "EXEC"})
        with self.assertRaises(PeerSessionError):
            validate_application_message({
                "version": 2,
                "type": "STATUS",
                "action": "request",
                "request_id": "x",
            })

    def test_error_message_is_bounded(self):
        valid = {
            "version": 1,
            "type": "ERROR",
            "code": "BAD_REQUEST",
            "message": "Invalid request",
        }
        self.assertEqual(validate_application_message(valid), valid)
        valid["message"] = "x" * 513
        with self.assertRaises(PeerSessionError):
            validate_application_message(valid)


if __name__ == "__main__":
    unittest.main()
