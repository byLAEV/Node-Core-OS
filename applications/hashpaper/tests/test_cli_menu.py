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
        default_document = Path("/tmp/synthetic-document.md")
        answers = ["7", "", "0"]
        with patch.object(cli, "_default_document_path", return_value=default_document):
            with patch("builtins.input", side_effect=answers):
                with patch.object(cli, "main", side_effect=[0]) as command:
                    self.assertEqual(cli.run_interactive_menu(), 0)
        command.assert_called_once_with([
            "proof-info", "--input", str(default_document)
        ])

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


if __name__ == "__main__":
    unittest.main()
