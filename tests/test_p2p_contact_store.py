import tempfile
import unittest
from pathlib import Path

from node_core.p2p.contact_store import (
    P2PContactError,
    P2PContactStore,
    validate_bitcoin_address,
)


class P2PContactStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = P2PContactStore(Path(self.temp.name))
        self.address = "1BoatSLRHtKNngkdXEeobR76b53LETtpyT"
        self.node_id = "sha256:" + "a" * 64

    def test_save_and_reload_contact(self):
        record = self.store.save_contact(
            bitcoin_address=self.address, node_id=self.node_id,
            host="192.0.2.15", port=4040, label="Nodo de prueba",
        )
        self.assertEqual(record["node_id"], self.node_id)
        reloaded = P2PContactStore(Path(self.temp.name)).get_by_bitcoin_address(self.address)
        self.assertEqual(reloaded["host"], "192.0.2.15")
        self.assertEqual(reloaded["port"], 4040)

    def test_invalid_address_rejected(self):
        for address in ("", "not-a-bitcoin-address", "bc1q invalid", "0BoatSLRHtKNngkdXEeobR76b53LETtpyT"):
            with self.subTest(address=address), self.assertRaises(P2PContactError):
                validate_bitcoin_address(address)

    def test_duplicate_node_id_rejected(self):
        self.store.save_contact(
            bitcoin_address=self.address, node_id=self.node_id,
            host="192.0.2.15", port=4040,
        )
        with self.assertRaises(P2PContactError):
            self.store.save_contact(
                bitcoin_address="3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
                node_id=self.node_id, host="192.0.2.16", port=4040,
            )

    def test_invalid_endpoint_rejected(self):
        with self.assertRaises(P2PContactError):
            self.store.save_contact(
                bitcoin_address=self.address, node_id=self.node_id,
                host="", port=4040,
            )
        with self.assertRaises(P2PContactError):
            self.store.save_contact(
                bitcoin_address=self.address, node_id=self.node_id,
                host="192.0.2.15", port=70000,
            )

    def test_remove_contact(self):
        self.store.save_contact(
            bitcoin_address=self.address, node_id=self.node_id,
            host="192.0.2.15", port=4040,
        )
        self.assertTrue(self.store.remove_contact(self.address))
        self.assertFalse(self.store.remove_contact(self.address))


if __name__ == "__main__":
    unittest.main()
