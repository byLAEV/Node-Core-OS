import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

from node_core.ui import MainMenu


class NativeNetworkStatusUITests(unittest.TestCase):
    def test_menu_labels_lan_and_wan_independently_and_truthfully(self):
        runtime = SimpleNamespace(
            native_p2p_status=lambda: {
                "discovered_peers": [{"node_id": "sha256:" + "a" * 64}],
                "discovery_running": True,
                "discovery_error": None,
                "active_peers": [{"node_id": "sha256:" + "b" * 64}],
                "wan_discovery_running": False,
                "wan_discovery_error": (
                    "WAN discovery requires a configured rendezvous/bootstrap service."
                ),
            }
        )
        menu = MainMenu(runtime)
        output = io.StringIO()

        with redirect_stdout(output):
            menu._print_native_network_indicator()

        rendered = output.getvalue()
        self.assertIn("Nodos locales detectados (incluido este nodo): 2", rendered)
        self.assertIn("Identidades remotas detectadas: 1", rendered)
        self.assertIn("Sesiones entrantes autenticadas: 1", rendered)
        self.assertIn("Manifiesto de consenso: PENDIENTE DE FIRMAS UNÁNIMES", rendered)
        self.assertIn("Native P2P worldwide discovery: NOT CONFIGURED", rendered)
        self.assertIn("configured rendezvous/bootstrap service", rendered)
        self.assertNotIn("worldwide discovery: ACTIVE", rendered)

    def test_menu_shows_lan_unavailable_and_worldwide_active_only_when_reported(self):
        runtime = SimpleNamespace(
            native_p2p_status=lambda: {
                "discovered_peers": [],
                "discovery_running": False,
                "discovery_error": "multicast unavailable",
                "active_peers": [],
                "wan_discovery_running": True,
                "wan_discovery_error": None,
            }
        )
        menu = MainMenu(runtime)
        output = io.StringIO()

        with redirect_stdout(output):
            menu._print_native_network_indicator()

        rendered = output.getvalue()
        self.assertIn("Node Core OS P2P LAN: UNAVAILABLE", rendered)
        self.assertIn("LAN discovery detail: multicast unavailable", rendered)
        self.assertIn("Native P2P worldwide discovery: ACTIVE", rendered)


if __name__ == "__main__":
    unittest.main()
