import tempfile
import unittest
from pathlib import Path

from node_core.content import ContentManager
from node_core.ipfs import AddedContent
from node_core.my_life import MyLifeBlog
from node_core.storage import StorageManager


class FakeKubo:
    def __init__(self):
        self.pinned = set()

    def add_file(self, path, pin=False):
        if pin:
            self.pinned.add("bafyblogtest")
        return AddedContent("bafyblogtest", path.name, path.stat().st_size)

    def pin_add(self, cid):
        self.pinned.add(cid)

    def pin_remove(self, cid):
        self.pinned.discard(cid)

    def pin_list(self):
        return {cid: {"Name": "entry.md", "Type": "recursive"} for cid in self.pinned}


class MyLifeBlogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.storage = StorageManager(root / "storage")
        self.storage.initialize()
        self.content = ContentManager(FakeKubo(), self.storage)
        self.blog = MyLifeBlog(self.storage, self.content)

    def test_entry_is_local_by_default(self):
        entry = self.blog.create_entry("First day", "A private life note.")
        self.assertIsNone(entry.cid)
        self.assertFalse(entry.pinned)
        self.assertTrue(Path(entry.text_path).is_file())
        self.assertEqual(Path(entry.text_path).read_text(encoding="utf-8"), "# First day\n\nA private life note.\n")
        self.assertEqual(self.blog.list_entries(), [entry])

    def test_entry_can_be_added_and_pinned_on_ipfs(self):
        entry = self.blog.create_entry("Milestone", "A note with an IPFS reference.", add_to_ipfs=True)
        self.assertEqual(entry.cid, "bafyblogtest")
        self.assertTrue(entry.pinned)
        self.assertEqual(self.blog.list_entries()[0].cid, "bafyblogtest")

    def test_empty_title_or_text_is_rejected(self):
        with self.assertRaises(ValueError):
            self.blog.create_entry(" ", "body")
        with self.assertRaises(ValueError):
            self.blog.create_entry("title", "  ")


if __name__ == "__main__":
    unittest.main()
