import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from node_core.ui import MainMenu


class FakeRuntime:
    def __init__(self, kubo_error=None, native_error=None):
        self.kubo_error = kubo_error
        self.native_error = native_error
        self.network = SimpleNamespace(status=self.kubo_status)

    def kubo_status(self):
        if self.kubo_error:
            raise RuntimeError(self.kubo_error)
        return SimpleNamespace(
            identity=SimpleNamespace(peer_id="QmLocalPeer12345678901234567890"),
            connected_peers=("QmPeerAlpha12345678901234567890",),
        )

    def native_p2p_status(self):
        if self.native_error:
            raise RuntimeError(self.native_error)
        return {
            "node_id": "sha256:local-node",
            "service_running": True,
            "listen_address": ("127.0.0.1", 4242),
            "trusted_count": 2,
            "revoked_count": 1,
            "active_peers": [
                {"node_id": "sha256:remote-node", "last_seen": "2026-10-15T08:00:00Z"}
            ],
            "last_error": None,
        }


class NetworkOverviewMenuTests(unittest.TestCase):
    def render(self, runtime):
        output = io.StringIO()
        with redirect_stdout(output):
            MainMenu(runtime)._network_overview()
        return output.getvalue()

    def test_dashboard_shows_kubo_and_native_status_separately(self):
        output = self.render(FakeRuntime())
        self.assertIn("Kubo / IPFS", output)
        self.assertIn("Estado: DISPONIBLE", output)
        self.assertIn("Conexiones directas: 1", output)
        self.assertIn("P2P nativo autenticado de Node Core OS", output)
        self.assertIn("Estado del listener: ACTIVO", output)
        self.assertIn("Peers de confianza: 2", output)
        self.assertIn("Sesiones entrantes autenticadas: 1", output)
        self.assertIn("sus peers no se suman", output)

    def test_kubo_failure_does_not_hide_native_p2p_status(self):
        output = self.render(FakeRuntime(kubo_error="Kubo is stopped"))
        self.assertIn("Kubo / IPFS", output)
        self.assertIn("Estado: NO DISPONIBLE", output)
        self.assertIn("Kubo is stopped", output)
        self.assertIn("P2P nativo autenticado de Node Core OS", output)
        self.assertIn("Estado del listener: ACTIVO", output)

    def test_native_p2p_failure_does_not_hide_kubo_status(self):
        output = self.render(FakeRuntime(native_error="cryptography is missing"))
        self.assertIn("Peer ID local: QmLocalPeer12345678901234567890", output)
        self.assertIn("Conexiones directas: 1", output)
        self.assertIn("P2P nativo autenticado de Node Core OS", output)
        self.assertIn("cryptography is missing", output)

    def test_network_menu_keeps_existing_choices_and_adds_dashboard(self):
        runtime = FakeRuntime()
        output = io.StringIO()
        with patch("builtins.input", side_effect=["13", "", "0"]), redirect_stdout(output):
            MainMenu(runtime).network_nodes()
        self.assertIn("13. Estado general de la red de nodos", output.getvalue())
        self.assertIn("Estado del listener: ACTIVO", output.getvalue())


if __name__ == "__main__":
    unittest.main()
