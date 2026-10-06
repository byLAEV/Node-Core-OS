from node_core.config import NodeConfig
from node_core.storage import StorageManager


def test_storage_stays_inside_root(tmp_path):
    storage = StorageManager(tmp_path)
    storage.initialize()
    assert storage.path("example.txt").parent == tmp_path


def test_default_config_has_kubo_api():
    assert NodeConfig().ipfs_api.startswith("http://")
