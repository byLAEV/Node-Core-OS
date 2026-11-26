import unittest

from node_core.p2p.session import PeerSessionError, validate_application_message


class P2PPeersProtocolTests(unittest.TestCase):
    def test_valid_peers_response_accepts_unique_node_ids(self):
        node_id = "sha256:" + "a" * 64
        message = {
            "version": 1,
            "type": "PEERS",
            "action": "response",
            "request_id": "request-1",
            "peers": [node_id],
        }
        self.assertEqual(validate_application_message(message), message)

    def test_peers_response_rejects_duplicate_node_ids(self):
        node_id = "sha256:" + "a" * 64
        message = {
            "version": 1,
            "type": "PEERS",
            "action": "response",
            "request_id": "request-1",
            "peers": [node_id, node_id],
        }
        with self.assertRaisesRegex(PeerSessionError, "duplicate"):
            validate_application_message(message)

    def test_peers_response_rejects_unhashable_malformed_entry_cleanly(self):
        message = {
            "version": 1,
            "type": "PEERS",
            "action": "response",
            "request_id": "request-1",
            "peers": [{"unexpected": "object"}],
        }
        with self.assertRaisesRegex(PeerSessionError, "invalid node ID"):
            validate_application_message(message)

    def test_peers_request_does_not_accept_peer_list(self):
        message = {
            "version": 1,
            "type": "PEERS",
            "action": "request",
            "request_id": "request-1",
            "peers": [],
        }
        with self.assertRaisesRegex(PeerSessionError, "must not include"):
            validate_application_message(message)


if __name__ == "__main__":
    unittest.main()
