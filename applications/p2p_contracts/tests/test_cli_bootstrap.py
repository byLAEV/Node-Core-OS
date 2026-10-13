"""Regression tests for genesis bootstrap when a node has no peer responses."""
import unittest
from unittest.mock import Mock

from applications.p2p_contracts.p2p_contracts.cli import P2PContractsCLI


GENESIS_HASH = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"


class GenesisBootstrapTests(unittest.TestCase):
    def make_cli(self, *, responses, manifest):
        cli = object.__new__(P2PContractsCLI)
        cli.service = Mock()
        cli.service.current_manifest.return_value = manifest
        cli.service._ensure_genesis_manifest.return_value = {"genesis_hash": GENESIS_HASH}
        cli.propagation = Mock()
        cli.propagation.query_status.side_effect = [
            {"active_proposals": [], "responses": responses},
            {"active_proposals": [], "responses": responses},
        ]
        cli.propagation.accept_new_propagation.return_value = {
            "proposal_hash": "proposal-hash",
            "accepted_at": "2026-01-01T00:00:00Z",
            "send_enabled_at": "2026-01-01T00:10:00Z",
        }
        cli._yes = Mock(return_value=True)
        cli.create_request_form = Mock(return_value=True)
        cli._start_owner_auto_submit = Mock()
        return cli

    def test_first_block_bootstrap_accepts_genesis_without_peer_responses(self):
        cli = self.make_cli(responses=[], manifest=None)

        cli.accept_propagation()

        cli.propagation.accept_new_propagation.assert_called_once_with(
            GENESIS_HASH, require_owner_request=True
        )
        saved_state = cli.propagation._save_state.call_args.args[0]
        self.assertTrue(saved_state["bootstrap_from_genesis"])
        self.assertEqual(saved_state["genesis_hash_accepted"], GENESIS_HASH)
        cli._start_owner_auto_submit.assert_called_once_with()

    def test_no_peer_responses_do_not_authorize_later_propagation(self):
        cli = self.make_cli(responses=[], manifest={"manifest_hash": "existing-head"})

        cli.accept_propagation()

        cli.propagation.accept_new_propagation.assert_not_called()
        cli.create_request_form.assert_not_called()

    def test_active_peer_proposal_still_blocks_genesis_bootstrap(self):
        cli = self.make_cli(responses=[], manifest=None)
        cli.propagation.query_status.side_effect = [
            {"active_proposals": [{"proposal_hash": "remote-proposal"}], "responses": []}
        ]

        cli.accept_propagation()

        cli.propagation.accept_new_propagation.assert_not_called()
        cli.create_request_form.assert_not_called()


if __name__ == "__main__":
    unittest.main()
