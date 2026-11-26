import subprocess
import unittest

from node_core.network import NodeNetwork


class FakeKubo:
    def __init__(self):
        self.calls = []

    def _run(self, *args):
        self.calls.append(args)
        if args == ("id",):
            return subprocess.CompletedProcess(
                args, 0,
                '{"ID":"QmNodeCorePeerId12345678901234567890",'
                '"Addresses":["/ip4/127.0.0.1/tcp/4001"]}',
                "",
            )
        if args == ("swarm", "peers"):
            return subprocess.CompletedProcess(
                args, 0,
                "/ip4/192.168.1.20/tcp/4001/p2p/QmPeerAlpha12345678901234567890\n"
                "/ip4/192.168.1.21/tcp/4001/p2p/QmPeerBeta12345678901234567890\n",
                "",
            )
        return subprocess.CompletedProcess(args, 0, "success\n", "")


class NodeNetworkTests(unittest.TestCase):
    def test_identity_uses_configured_kubo(self):
        kubo = FakeKubo()
        identity = NodeNetwork(kubo).identity()
        self.assertEqual(identity.peer_id, "QmNodeCorePeerId12345678901234567890")
        self.assertEqual(kubo.calls, [("id",)])

    def test_connected_peers_returns_unique_peer_ids(self):
        kubo = FakeKubo()
        peers = NodeNetwork(kubo).connected_peers()
        self.assertEqual(len(peers), 2)
        self.assertIn("QmPeerAlpha12345678901234567890", peers)

    def test_connect_rejects_incomplete_address(self):
        with self.assertRaises(ValueError):
            NodeNetwork(FakeKubo()).connect("/ip4/192.168.1.20/tcp/4001")

    def test_connect_runs_kubo_swarm_connect(self):
        kubo = FakeKubo()
        address = "/ip4/192.168.1.20/tcp/4001/p2p/QmPeerAlpha12345678901234567890"
        NodeNetwork(kubo).connect(address)
        self.assertEqual(kubo.calls[-1], ("swarm", "connect", address))

    def test_ping_rejects_invalid_peer_id(self):
        with self.assertRaises(ValueError):
            NodeNetwork(FakeKubo()).ping("not a peer id")

    def test_ping_runs_one_round_trip(self):
        kubo = FakeKubo()
        peer_id = "QmPeerAlpha12345678901234567890"
        output = NodeNetwork(kubo).ping(peer_id)
        self.assertIn("success", output)
        self.assertEqual(kubo.calls[-1], ("ping", "-n", "1", peer_id))


if __name__ == "__main__":
    unittest.main()
