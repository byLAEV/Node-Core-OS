"""Tests for the HashPaper menu used by the Node Core OS Applications launcher."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hashpaper.cli as cli


class HashPaperMenuTests(unittest.TestCase):
    def test_launcher_without_arguments_opens_interactive_menu(self):
        with patch.object(sys, "argv", ["main.py"]):
            with patch.object(cli, "run_interactive_menu", return_value=0) as menu:
                self.assertEqual(cli.main(), 0)
        menu.assert_called_once_with()

    def test_create_menu_option_builds_expected_cli_arguments(self):
        answers = [
            "1",
            "/tmp/hashpaper-menu-test.md",
            "Synthetic title",
            "Synthetic body",
            "",
            "0",
        ]
        with patch("builtins.input", side_effect=answers):
            with patch.object(cli, "main", side_effect=[0]) as command:
                self.assertEqual(cli.run_interactive_menu(), 0)
        command.assert_called_once_with([
            "create",
            "--output", "/tmp/hashpaper-menu-test.md",
            "--title", "Synthetic title",
            "--text", "Synthetic body",
        ])

    def test_menu_rejects_unknown_choice_and_can_exit(self):
        with patch("builtins.input", side_effect=["unknown", "0"]):
            self.assertEqual(cli.run_interactive_menu(), 0)


if __name__ == "__main__":
    unittest.main()
