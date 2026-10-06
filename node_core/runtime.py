"""Runtime orchestration for Node Core OS."""
from node_core.config import NodeConfig
from node_core.content import ContentManager
from node_core.ipfs import KuboManager
from node_core.storage import StorageManager
from node_core.ui import MainMenu
class NodeRuntime:
    def __init__(self):
        self.config=NodeConfig.load(); self.storage=StorageManager(self.config.local_storage_path)
        self.kubo=KuboManager(self.config.ipfs_executable,self.config.ipfs_repo_path,self.config.ipfs_api,self.config.ipfs_profile)
        self.content=ContentManager(self.kubo,self.storage); self._booted=False
    @property
    def ipfs(self): return self.kubo
    def boot(self):
        self.config.ensure_directories(); self.storage.initialize(); self.config.save(); self._booted=True
    def menu(self):
        if not self._booted: raise RuntimeError("Node Runtime must be booted before opening the menu.")
        MainMenu(self).run()
