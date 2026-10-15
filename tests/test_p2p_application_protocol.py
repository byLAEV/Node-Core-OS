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

    def test_peers_message_is_bounded_and_validated(self):
        message = {
            "version": 1,
            "type": "PEERS",
            "peers": ["sha256:" + "a" * 64],
        }
        self.assertEqual(validate_application_message(message), message)
        message["peers"] = ["not-a-node-id"]
        with self.assertRaises(PeerSessionError):
            validate_application_message(message)

        message["peers"] = ["sha256:" + "a" * 64] * 101
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
