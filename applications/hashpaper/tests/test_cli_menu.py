"""Tests for the HashPaper menu used by the Node Core OS Applications launcher."""

from pathlib import Path
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hashpaper.cli as cli


class HashPaperMenuTests(unittest.TestCase):
    def setUp(self):
        self.consent_patch = patch.object(cli, "_authorize_identity_session", return_value=True)
        self.consent_patch.start()
        cli._SESSION_IDENTITY = {
            "identity_id": "synthetic-identity",
            "full_name": "Synthetic Test Person",
            "identity_status": "declared",
        }
        cli._SESSION_PEER_ID = "12D3KooW-synthetic"

    def tearDown(self):
        self.consent_patch.stop()
        cli._SESSION_IDENTITY = None
        cli._SESSION_PEER_ID = None

    def test_launcher_without_arguments_opens_interactive_menu(self):
        with patch.object(sys, "argv", ["main.py"]):
            with patch.object(cli, "run_interactive_menu", return_value=0) as menu:
                self.assertEqual(cli.main(), 0)
        menu.assert_called_once_with()

    def test_create_menu_uses_default_path_without_asking_for_it(self):
        answers = ["1", "Synthetic title", "Synthetic body", "", "0"]
        with patch("builtins.input", side_effect=answers):
            with patch.object(cli, "main", side_effect=[0]) as command:
                self.assertEqual(cli.run_interactive_menu(), 0)
        command.assert_called_once_with([
            "create", "--title", "Synthetic title", "--text", "Synthetic body"
        ])

    def test_proof_info_menu_uses_default_document_without_path_prompt(self):
        with tempfile.TemporaryDirectory() as temporary:
            default_document = Path(temporary) / "synthetic-document.md"
            default_document.write_text("synthetic", encoding="utf-8")
            answers = ["7", "", "0"]
            with patch.object(cli, "_default_document_path", return_value=default_document):
                with patch("builtins.input", side_effect=answers):
                    with patch.object(cli, "main", side_effect=[0]) as command:
                        self.assertEqual(cli.run_interactive_menu(), 0)
            command.assert_called_once_with([
                "proof-info", "--input", str(default_document)
            ])

    def test_check_and_upgrade_menu_select_document_with_a_proof(self):
        with tempfile.TemporaryDirectory() as temporary:
            original = Path(temporary) / "Genesis-HashPaper.md"
            original.write_text("synthetic", encoding="utf-8")
            Path(str(original) + ".ots").write_bytes(b"synthetic proof")
            for choice, command_name in (("3", "check"), ("4", "upgrade")):
                with patch.object(cli, "_default_document_path", return_value=original) as select:
                    with patch("builtins.input", side_effect=[choice, "", "0"]):
                        with patch.object(cli, "main", return_value=0) as command:
                            self.assertEqual(cli.run_interactive_menu(), 0)
                select.assert_called_once_with(require_proof=True)
                command.assert_called_once_with([command_name, "--input", str(original)])

    def test_create_menu_cancels_when_zero_is_entered_as_title(self):
        with patch("builtins.input", side_effect=["1", "0", "0"]):
            with patch.object(cli, "main") as command:
                self.assertEqual(cli.run_interactive_menu(), 0)
        command.assert_not_called()

    def test_environment_variables_are_expanded_in_explicit_paths(self):
        with patch.dict(os.environ, {"HASH_PAPER_TEST_PATH": "/tmp/expanded.md"}):
            self.assertEqual(cli._expanded_path("$HASH_PAPER_TEST_PATH"), Path("/tmp/expanded.md"))


    def test_proof_info_reports_original_and_proof_fingerprints_as_pending(self):
        with tempfile.TemporaryDirectory() as temporary:
            original = Path(temporary) / "synthetic.md"
            proof = Path(str(original) + ".ots")
            report = Path(temporary) / "proof-info.json"
            original.write_text("synthetic document\\n", encoding="utf-8")
            proof.write_bytes(b"synthetic ots proof bytes")
            fake_result = SimpleNamespace(
                status="WAITING_FOR_BITCOIN",
                proof_verification="PENDING",
                bitcoin_block_height=None,
                return_code=0,
                stdout="Pending confirmation in Bitcoin blockchain",
                stderr="",
            )
            output = io.StringIO()
            with patch.object(cli, "OpenTimestampsClient") as client_class:
                client_class.return_value.check.return_value = fake_result
                with contextlib.redirect_stdout(output):
                    status = cli.main([
                        "proof-info", "--input", str(original), "--report", str(report)
                    ])
            self.assertEqual(status, 0)
            result = json.loads(output.getvalue().split("Timestamp proof exists", 1)[0])
            self.assertEqual(result["status"], "WAITING_FOR_BITCOIN")
            self.assertEqual(result["proof_verification"], "PENDING")
            self.assertEqual(len(result["original_sha256"]), 64)
            self.assertEqual(len(result["proof_file_sha256"]), 64)
            self.assertIn("not an official OpenTimestamps-issued identifier", result["proof_fingerprint_note"])
            saved = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(saved["proof_file_sha256"], result["proof_file_sha256"])

    def test_menu_rejects_unknown_choice_and_can_exit(self):
        with patch("builtins.input", side_effect=["unknown", "0"]):
            self.assertEqual(cli.run_interactive_menu(), 0)


    def test_create_embeds_session_identity_and_uses_application_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            old_dir = os.environ.get("NODE_CORE_DATA_DIR")
            try:
                os.environ["NODE_CORE_DATA_DIR"] = temporary
                output = Path(temporary) / "hashpaper" / "documents" / "Synthetic-Title.md"
                with patch.object(cli, "_default_document_path", return_value=output):
                    status = cli.main(["create", "--title", "Synthetic Title", "--text", "Synthetic body"])
                self.assertEqual(status, 0)
                text = output.read_text(encoding="utf-8")
                self.assertIn("Synthetic body", text)
                self.assertIn("synthetic-identity", text)
                self.assertIn("12D3KooW-synthetic", text)
            finally:
                if old_dir is None:
                    os.environ.pop("NODE_CORE_DATA_DIR", None)
                else:
                    os.environ["NODE_CORE_DATA_DIR"] = old_dir

    def test_identity_consent_requires_exact_phrase(self):
        with patch("builtins.input", return_value="yes"):
            self.assertFalse(cli._authorize_identity_session())


if __name__ == "__main__":
    unittest.main()
