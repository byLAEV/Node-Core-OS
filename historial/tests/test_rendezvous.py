import unittest

from node_core.p2p.rendezvous import NativeP2PRendezvousClient


class RendezvousClientValidationTests(unittest.TestCase):
    def test_rejects_plain_http_endpoint(self):
        with self.assertRaises(ValueError):
            NativeP2PRendezvousClient("http://rendezvous.example")

    def test_rejects_credentials_in_endpoint(self):
        with self.assertRaises(ValueError):
            NativeP2PRendezvousClient("https://user:password@rendezvous.example")

    def test_rejects_query_in_endpoint(self):
        with self.assertRaises(ValueError):
            NativeP2PRendezvousClient("https://rendezvous.example?token=secret")

    def test_rejects_invalid_timeout(self):
        with self.assertRaises(ValueError):
            NativeP2PRendezvousClient("https://rendezvous.example", timeout_seconds=0)

    def test_rejects_invalid_response_limit(self):
        with self.assertRaises(ValueError):
            NativeP2PRendezvousClient("https://rendezvous.example", max_response_bytes=10)

    def test_requires_valid_node_id_before_peer_query(self):
        client = NativeP2PRendezvousClient("https://rendezvous.example")
        with self.assertRaises(ValueError):
            client.peers("not-a-node-id")


if __name__ == "__main__":
    unittest.main()
