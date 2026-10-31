"""Two-node integration tests for GitHub Page record replication."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.p2p.secure_messaging import NodeRSAIdentityStore
from node_core.p2p.service import NodePeerService
from node_core.p2p.tls_transport import NodeTLSTransport
from node_core.record_replication import NodeRecordReplicator, RecordReplicationError


class RecordReplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.store_a = NodeIdentityStore(root / "node-a")
        self.store_b = NodeIdentityStore(root / "node-b")
        self.meta_a = self.store_a.initialize()
        self.meta_b = self.store_b.initialize()
        self.tls_a = NodeTLSTransport(self.store_a)
        self.tls_b = NodeTLSTransport(self.store_b)
        self.cert_a = self.tls_a.ensure_certificate()
        self.cert_b = self.tls_b.ensure_certificate()
        self.rsa_a = NodeRSAIdentityStore(self.store_a)
        self.rsa_b = NodeRSAIdentityStore(self.store_b)
        self.rsa_a.initialize()
        self.rsa_b.initialize()
        self.replica_a = NodeRecordReplicator(root / "node-a", self.store_a)
        self.replica_b = NodeRecordReplicator(root / "node-b", self.store_b)

    def make_record(self):
        return {
            "schema": NodeRecordReplicator.RECORD_SCHEMA,
            "record_id": "8c4a3e21-4e15-4c93-9c5e-4d28f13c67a1",
            "node_id": self.meta_a["node_id"],
            "github_account": "operator-a",
            "repository": "operator-a/node-core-client",
            "source_pages_url": "https://operator-a.github.io/node-core-client/",
            "created_at_utc": "2026-10-31T08:00:00+00:00",
            "fields": {"message": "hello from node A"},
            "sync_status": "synced",
        }

    def test_two_nodes_replicate_record_and_deduplicate_repeated_delivery(self):
        server = NodePeerService(
            identity_store=self.store_b,
            tls_transport=self.tls_b,
            trusted_peers={self.meta_a["node_id"]: self.cert_a},
            rsa_identity_store=self.rsa_b,
            trusted_rsa_public_keys={self.meta_a["node_id"]: self.rsa_a.public_key_pem()},
            on_message=lambda peer, message_id, text: self.replica_b.receive_message(peer, message_id, text),
            timeout_seconds=5,
        )
        host, port = server.start()
        self.addCleanup(server.stop)

        client = NodePeerService(
            identity_store=self.store_a,
            tls_transport=self.tls_a,
            trusted_peers={self.meta_b["node_id"]: self.cert_b},
            rsa_identity_store=self.rsa_a,
            trusted_rsa_public_keys={self.meta_b["node_id"]: self.rsa_b.public_key_pem()},
            timeout_seconds=5,
        )
        record = self.make_record()
        first = self.replica_a.send_record(
            client, host, port, self.meta_b["node_id"], self.rsa_b.public_key_pem(), record
        )
        second = self.replica_a.send_record(
            client, host, port, self.meta_b["node_id"], self.rsa_b.public_key_pem(), record
        )

        self.assertEqual(first["status"], "accepted")
        self.assertEqual(second["status"], "accepted")
        received = self.replica_b.list_received(self.meta_a["node_id"])
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["record"], record)
        self.assertEqual(received[0]["source_repository"], "operator-a/node-core-client")
        self.assertEqual(received[0]["replica_node_id"], self.meta_b["node_id"])

    def test_replica_rejects_sender_identity_mismatch(self):
        event = {
            "schema": NodeRecordReplicator.SCHEMA,
            "event_id": self.make_record()["record_id"],
            "origin_node_id": self.meta_b["node_id"],
            "recipient_node_id": self.meta_b["node_id"],
            "repository": "operator-a/node-core-client",
            "record": self.make_record(),
        }
        with self.assertRaisesRegex(RecordReplicationError, "authenticated P2P sender"):
            self.replica_b.receive_message(
                {"node_id": self.meta_a["node_id"]}, "message-1",
                json.dumps(event),
            )

    def test_non_replication_message_is_ignored(self):
        self.assertFalse(
            self.replica_b.receive_message(
                {"node_id": self.meta_a["node_id"]}, "message-2",
                json.dumps({"schema": "other/event", "value": 1}),
            )
        )
        self.assertEqual(self.replica_b.list_received(), [])


if __name__ == "__main__":
    unittest.main()
