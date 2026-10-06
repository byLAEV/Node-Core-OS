"""Runtime orchestration for Node Core OS."""

from node_core.config import NodeConfig
from node_core.storage import StorageManager
from node_core.ipfs import IPFSClient
from node_core.ui import MainMenu


class NodeRuntime:
    """Owns shared infrastructure and coordinates BIOS/Core interfaces."""

    def __init__(self) -> None:
        self.config = NodeConfig.load()
        self.storage = StorageManager(self.config.local_storage_path)
        self.ipfs = IPFSClient(self.config.ipfs_api)
        self._booted = False

    def boot(self) -> None:
        self.config.ensure_directories()
        self.storage.initialize()
        self._booted = True

    def menu(self) -> None:
        if not self._booted:
            raise RuntimeError("Node Runtime must be booted before opening the menu.")
        MainMenu(self).run()
