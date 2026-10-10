"""Runtime orchestration for Node Core OS."""

from node_core.config import NodeConfig
from node_core.content import ContentManager
from node_core.evidence import EvidenceManager
from node_core.ipfs import KuboManager
from node_core.my_life import MyLifeBlog
from node_core.storage import StorageManager
from node_core.ui import MainMenu


class NodeRuntime:
    """Owns shared infrastructure and coordinates BIOS/Core interfaces."""

    def __init__(self) -> None:
        self.config = NodeConfig.load()
        self.storage = StorageManager(self.config.local_storage_path)
        self.kubo = KuboManager(
            executable=self.config.ipfs_executable,
            repo_path=self.config.ipfs_repo_path,
            api=self.config.ipfs_api,
            profile=self.config.ipfs_profile,
        )
        self.content = ContentManager(
            self.kubo,
            self.storage,
            gateway=self.config.ipfs_gateway,
        )
        self.evidence = EvidenceManager(self.content)
        self.my_life = MyLifeBlog(self.storage, self.content)
        self._booted = False

    @property
    def ipfs(self) -> KuboManager:
        return self.kubo

    def boot(self) -> None:
        self.config.ensure_directories()
        self.storage.initialize()
        self.config.save()
        self._booted = True

    def menu(self) -> None:
        if not self._booted:
            raise RuntimeError("Node Runtime must be booted before opening the menu.")
        MainMenu(self).run()
