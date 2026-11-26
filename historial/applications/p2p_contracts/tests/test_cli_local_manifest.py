"""Tests that local manifest creation is independent of peer discovery."""
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from applications.p2p_contracts.p2p_contracts.cli import P2PContractsCLI


class LocalManifestCreationTests(unittest.TestCase):
    def test_local_only_request_creates_manifest_without_pubsub_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            request_path = Path(directory) / "request.json"
            request_document = {
                "request_id": "request-test",
                "requester": {"node_id": "peer-local-test"},
            }
            request_path.write_text(json.dumps(request_document), encoding="utf-8")
            manifest = {
                "sequence": 1,
                "manifest_hash": "manifest-hash-test",
                "genesis_hash": "genesis-hash-test",
            }
            cli = object.__new__(P2PContractsCLI)
            cli.runtime = Mock()
            cli.runtime.identity_profile.load.return_value = {}
            cli.runtime.network.identity.return_value = Mock(
                peer_id="peer-local-test", addresses=()
            )
            cli.service = Mock()
            cli.service.create_btc_exchange_request.return_value = {
                "request_id": "request-test",
                "request_hash": "request-hash-test",
                "manifest_hash": "manifest-hash-test",
                "manifest_sequence": 1,
                "node_id": "peer-local-test",
                "request_path": str(request_path),
                "manifest_path": str(Path(directory) / "manifest.json"),
                "identity_fields_published": [],
                "status": "LOCAL_ONLY",
                "manifest_document": manifest,
            }
            cli.propagation = Mock()
            cli._ask = Mock(side_effect=[
                "email", "local@example.invalid", "", "0.01", "USDT",
                "100", "", "Local-only test request",
            ])
            cli._yes = Mock(side_effect=[False, True])

            output = StringIO()
            with redirect_stdout(output):
                created = cli.create_request_form(local_only=True)

            self.assertTrue(created)
            cli.service.create_btc_exchange_request.assert_called_once()
            cli.propagation.publish_request.assert_not_called()
            cli.propagation.query_status.assert_not_called()
            self.assertIn("Status: LOCAL_ONLY_UNCORROBORATED", output.getvalue())
            self.assertIn("No peer discovery or PubSub response was required", output.getvalue())


if __name__ == "__main__":
    unittest.main()
