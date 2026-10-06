import json

from node_core.config import NodeConfig
from node_core.content import ContentManager
from node_core.ipfs import AddedContent
from node_core.ipfs import KuboManager
from node_core.storage import StorageManager


class FakeKubo:
    def add_file(self, path, pin=False):
        return AddedContent("bafytestcid", path.name, path.stat().st_size)

    def cat(self, cid):
        if cid != "bafytestcid":
            raise ValueError("bad cid")
        return b"node-core"

    def pin_add(self, cid):
        if cid != "bafytestcid":
            raise ValueError("bad cid")

    def pin_remove(self, cid):
        if cid != "bafytestcid":
            raise ValueError("bad cid")

    def pin_list(self):
        return {"bafytestcid": {"Name": "test.txt", "Type": "recursive"}}


def test_storage_stays_inside_root(tmp_path):
    storage = StorageManager(tmp_path)
    storage.initialize()
    assert storage.path("example.txt").parent == tmp_path


def test_storage_writes_and_reads(tmp_path):
    storage = StorageManager(tmp_path)
    storage.write_bytes("documents/test.txt", b"node")
    assert storage.read_bytes("documents/test.txt") == b"node"


def test_storage_rejects_escape(tmp_path):
    storage = StorageManager(tmp_path)
    try:
        storage.path("../outside.txt")
    except ValueError:
        pass
    else:
        raise AssertionError("Storage path traversal was not rejected")


def test_config_persists_kubo_settings(tmp_path):
    config = NodeConfig(
        data_dir=tmp_path,
        local_storage_path=tmp_path / "storage",
        ipfs_repo_path=tmp_path / "ipfs",
    )
    config.save()
    loaded = NodeConfig.load()
    assert loaded.ipfs_repo_path == tmp_path / "ipfs"
    assert json.loads(config.config_path.read_text())["ipfs_profile"] == "unixfs-v1-2025"


def test_kubo_status_without_binary(tmp_path):
    manager = KuboManager(
        executable="definitely-not-installed-node-core-kubo",
        repo_path=tmp_path / "ipfs",
        api="http://127.0.0.1:5001",
    )
    status = manager.status()
    assert status.installed is False
    assert status.running is False


def test_content_add_and_retrieve(tmp_path):
    source = tmp_path / "source.txt"
    source.write_bytes(b"node-core")
    manager = ContentManager(FakeKubo(), StorageManager(tmp_path / "storage"))

    result = manager.add(source)
    assert result.cid == "bafytestcid"
    assert result.size == 9

    destination = tmp_path / "out.txt"
    manager.retrieve(result.cid, destination)
    assert destination.read_bytes() == b"node-core"


def test_content_pinning(tmp_path):
    manager = ContentManager(FakeKubo(), StorageManager(tmp_path / "storage"))
    manager.pin("bafytestcid")
    manager.unpin("bafytestcid")
    assert "bafytestcid" in manager.pins()
