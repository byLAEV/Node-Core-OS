import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from node_core.bios import BIOSMenu
from node_core.ui import MainMenu


class BIOSMenuTests(unittest.TestCase):
    def test_menu_dispatches_every_bios_section(self):
        runtime = SimpleNamespace()
        menu = BIOSMenu(runtime)
        calls = []
        names = ["storage", "kubo", "network", "services", "configuration",
                 "security", "diagnostics", "updates", "lifecycle",
                 "identity", "domain_verification"]
        for name in names:
            setattr(menu, name, lambda name=name: calls.append(name))
        with patch("builtins.input", side_effect=[str(i) for i in range(1, 12)] + ["0"]), patch("builtins.print"):
            menu.run()
        self.assertEqual(calls, names)

    def test_ui_delegates_to_bios_module(self):
        runtime = SimpleNamespace()
        with patch("node_core.bios.BIOSMenu.run") as run:
            MainMenu(runtime).bios()
        run.assert_called_once()

    def test_bios_refuses_root_execution(self):
        menu = BIOSMenu(SimpleNamespace())
        with patch("node_core.bios.os.geteuid", return_value=0):
            with self.assertRaisesRegex(RuntimeError, "user-only"):
                menu.run()

    def test_defaults_and_descriptions_are_visible(self):
        menu = BIOSMenu(SimpleNamespace())
        with patch("builtins.input", side_effect=["0"]), patch("builtins.print") as output:
            menu.run()
        rendered = "\\n".join(str(call.args[0]) for call in output.call_args_list if call.args)
        self.assertIn("Local private/shared storage", rendered)
        self.assertIn("Kubo daemon", rendered)
        self.assertIn("Network Domain Verification", rendered)


if __name__ == "__main__":
    unittest.main()
