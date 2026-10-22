import io
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from types import SimpleNamespace

from node_core.ui import MainMenu


class NativeNetworkStatusUITests(unittest.TestCase):
    def test_menu_labels_lan_and_wan_independently_and_truthfully(self):
        runtime = SimpleNamespace(
            native_p2p_status=lambda: {
                "node_id": "sha256:" + "c" * 64,
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
        self.assertIn("Nodos online verificados: 2 (incluido este nodo)", rendered)
        self.assertIn("Pares remotos: 1", rendered)
        self.assertIn("Nodos detectados en LAN (anuncio firmado, sesión no autenticada):", rendered)
        self.assertIn("Manifiesto de consenso: PENDIENTE DE FIRMAS UNÁNIMES", rendered)
        self.assertIn("Native P2P worldwide discovery: NOT CONFIGURED", rendered)
        self.assertIn("configured rendezvous/bootstrap service", rendered)
        self.assertNotIn("worldwide discovery: ACTIVE", rendered)

    def test_menu_shows_lan_unavailable_and_worldwide_active_only_when_reported(self):
        runtime = SimpleNamespace(
            native_p2p_status=lambda: {
                "node_id": "sha256:" + "c" * 64,
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

    def test_main_menu_option_six_refreshes_network_and_returns_to_updated_header(self):
        status_calls = []
        runtime = SimpleNamespace(
            identity_profile=SimpleNamespace(load=lambda: None),
            native_p2p_status=lambda: status_calls.append(True) or {
                "node_id": "sha256:" + "c" * 64,
                "discovered_peers": [],
                "discovery_running": True,
                "discovery_error": None,
                "active_peers": [],
                "wan_discovery_running": False,
                "wan_discovery_error": "No rendezvous service is configured.",
            },
            refresh_network_status=lambda: {"kubo": None, "errors": []},
        )
        menu = MainMenu(runtime)
        update_status = SimpleNamespace(
            available=False, checked=True, local_version="1.5.4",
            remote_version=None, message="current"
        )
        output = io.StringIO()
        with (
            patch("node_core.ui.check_for_updates", return_value=update_status),
            patch("builtins.input", side_effect=["6", "", "0"]),
            redirect_stdout(output),
        ):
            menu.run()
        rendered = output.getvalue()
        self.assertIn("6. Refresh", rendered)
        self.assertIn("Refreshing Node Core OS network status...", rendered)
        self.assertIn("Network refresh complete.", rendered)
        self.assertGreaterEqual(len(status_calls), 2)

    def test_refresh_displays_kubo_peers_bootstrap_and_wan_truthfully(self):
        runtime = SimpleNamespace(
            refresh_network_status=lambda: {
                "kubo": SimpleNamespace(
                    running=True, installed=True, initialized=True,
                    peer_id="QmLocalPeer", version="0.42.0", detail=None
                ),
                "kubo_connected_peers": ["QmRemotePeer"],
                "kubo_bootstrap_peers": ["/dnsaddr/bootstrap.example/p2p/QmBootstrap"],
                "native_p2p": {
                    "discovery_running": True,
                    "recently_authenticated_peers": [],
                    "active_peers": [],
                    "wan_discovery_running": False,
                    "wan_discovery_error": "No verified rendezvous service is configured.",
                },
                "errors": [],
            }
        )
        menu = MainMenu(runtime)
        output = io.StringIO()
        with patch("builtins.input", return_value=""), redirect_stdout(output):
            menu.refresh_network()
        rendered = output.getvalue()
        self.assertIn("Kubo connected peers: 1", rendered)
        self.assertIn("KUBO PEER QmRemotePeer", rendered)
        self.assertIn("Kubo configured bootstrap entries: 1", rendered)
        self.assertIn("Native P2P worldwide discovery: NOT CONFIGURED", rendered)
        self.assertNotIn("Native P2P worldwide discovery: CONFIGURED — ACTIVE", rendered)


    def test_main_menu_footer_summarizes_live_network_state_before_first_refresh(self):
        runtime = SimpleNamespace(
            native_p2p_status=lambda: {
                "discovery_running": True,
                "active_peers": [{"node_id": "sha256:" + "a" * 64}],
                "recently_authenticated_peers": [],
                "wan_discovery_running": False,
                "wan_discovery_error": "No verified rendezvous service is active.",
            },
            kubo=SimpleNamespace(
                status=lambda: SimpleNamespace(running=True)
            ),
        )
        menu = MainMenu(runtime)
        output = io.StringIO()

        with redirect_stdout(output):
            menu._print_network_report()

        rendered = output.getvalue()
        self.assertIn("Report:", rendered)
        self.assertIn("Native P2P LAN: RUNNING; authenticated remote nodes: 1", rendered)
        self.assertIn("Native P2P worldwide discovery: NOT CONFIGURED", rendered)
        self.assertIn("Kubo/IPFS: RUNNING", rendered)
        self.assertIn("press 6. Refresh", rendered)
        self.assertIn("not proof of an active native WAN connection", rendered)

    def test_main_menu_footer_reports_refresh_warnings(self):
        runtime = SimpleNamespace(
            native_p2p_status=lambda: {},
            kubo=SimpleNamespace(status=lambda: None),
        )
        menu = MainMenu(runtime)
        menu._last_refresh_result = {
            "native_p2p": {
                "discovery_running": False,
                "active_peers": [],
                "recently_authenticated_peers": [],
                "wan_discovery_running": False,
                "wan_discovery_error": "WAN service missing",
            },
            "kubo": None,
            "kubo_connected_peers": [],
            "kubo_bootstrap_peers": [],
            "errors": ["Kubo status: daemon not running"],
        }
        output = io.StringIO()

        with redirect_stdout(output):
            menu._print_network_report()

        rendered = output.getvalue()
        self.assertIn("Refresh result: 1 warning/error(s) require attention.", rendered)
        self.assertIn("Kubo status: daemon not running", rendered)


if __name__ == "__main__":
    unittest.main()
