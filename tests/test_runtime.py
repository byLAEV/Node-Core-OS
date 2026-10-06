from node_core.content import ContentManager
from node_core.ipfs import AddedContent, KuboManager
from node_core.storage import StorageManager

class FakeKubo:
    def add_file(self,path,pin=False): return AddedContent("bafytestcid",path.name,path.stat().st_size)
    def cat(self,cid):
        if cid!="bafytestcid": raise ValueError("bad cid")
        return b"node-core"
    def pin_add(self,cid): pass
    def pin_remove(self,cid): pass
    def pin_list(self): return {"bafytestcid":{"Name":"test.txt","Type":"recursive"}}

def test_content_registry_persists(tmp_path):
    source=tmp_path/"source.txt"; source.write_bytes(b"node-core")
    manager=ContentManager(FakeKubo(),StorageManager(tmp_path/"storage"))
    result=manager.add(source)
    assert result.cid=="bafytestcid" and result.pinned is False
    assert manager.get(result.cid).source_path==str(source.resolve())
    assert manager.get(result.cid).provenance=={}
    manager.pin(result.cid); assert manager.get(result.cid).pinned is True
    manager.unpin(result.cid); assert manager.get(result.cid).pinned is False

def test_unknown_pin_does_not_create_record(tmp_path):
    manager=ContentManager(FakeKubo(),StorageManager(tmp_path/"storage"))
    manager.pin("bafytestcid")
    assert manager.get("bafytestcid") is None
