"""Unit tests for the Termux remote Kubo read helper."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from node_core.identity.node_identity import NodeIdentityStore
from tools import termux_remote_kubo_read as helper


class TermuxRemoteKuboReadTests(unittest.TestCase):
    def setUp(self):
        if os.getuid() == 0:
            self.skipTest("Node Core OS tests must run as a normal user.")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data_dir = self.root / ".node-core"
        self.store = NodeIdentityStore(self.data_dir)
        self.identity = self.store.initialize()
        self.content = b"synthetic remote Kubo content\n"
        self.expected_hash = hashlib.sha256(self.content).hexdigest()
        self.args = Namespace(
            peer_address="/dns4/bore.pub/tcp/12345/p2p/QmSyntheticPeer",
            cid="bafybeisyntheticcid",
            expected_sha256=self.expected_hash,
            nonce="test-nonce-12345678901234567890",
            ack_url="http://bore.pub:23456/ack",
            data_dir=self.data_dir,
            app_root=Path(__file__).resolve().parents[1],
            ipfs_executable="/usr/bin/ipfs",
            ipfs_path=self.root / "ipfs",
        )

    def test_reads_content_and_submits_a_verifiable_signed_receipt(self):
        commands = [
            SimpleNamespace(returncode=0, stdout="", stderr=""),
            SimpleNamespace(returncode=0, stdout=self.content, stderr=b""),
        ]
        response = MagicMock()
        response.status = 200
        response.read.return_value = b"PASS: signed receipt verified"
        response.__enter__.return_value = response

        with (
            patch.object(helper, "parse_args", return_value=self.args),
            patch.object(helper.subprocess, "run", side_effect=commands) as run,
            patch.object(helper, "urlopen", return_value=response) as post,
        ):
            self.assertEqual(helper.main(), 0)

        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0][1:3], ["swarm", "connect"])
        self.assertEqual(run.call_args_list[1].args[0][1:3], ["cat", self.args.cid])
        request = post.call_args.args[0]
        receipt = json.loads(request.data.decode("utf-8"))
        signed = {key: receipt[key] for key in ("schema", "run_nonce", "node_id", "cid", "sha256")}
        self.assertEqual(receipt["node_id"], self.identity["node_id"])
        self.assertEqual(receipt["sha256"], self.expected_hash)
        self.assertTrue(
            NodeIdentityStore.verify(
                receipt["public_key"], helper.canonical_json(signed), bytes.fromhex(receipt["signature"])
            )
        )
        self.assertNotIn("private_key", receipt)
        self.assertNotIn("node.key", request.data.decode("utf-8"))

    def test_refuses_to_sign_when_retrieved_hash_does_not_match(self):
        commands = [
            SimpleNamespace(returncode=0, stdout="", stderr=""),
            SimpleNamespace(returncode=0, stdout=b"different content", stderr=b""),
        ]
        with (
            patch.object(helper, "parse_args", return_value=self.args),
            patch.object(helper.subprocess, "run", side_effect=commands),
            patch.object(helper, "urlopen") as post,
        ):
            with self.assertRaises(SystemExit):
                helper.main()
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
