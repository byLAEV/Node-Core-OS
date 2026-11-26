"""Tests for the persistent external CID reference library."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from node_core.external_cids import ExternalCIDError, ExternalCIDLibrary
from node_core.storage import StorageManager


class ExternalCIDLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "storage"
        self.storage = StorageManager(self.root)
        self.storage.initialize()
        self.kubo = Mock()
        self.library = ExternalCIDLibrary(self.storage, self.kubo)
        self.cid = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3l5p6g3v6w3m6q7z7q2x2x2x4"

    def test_add_and_reload_reference(self):
        reference = self.library.add(self.cid, "External document", source_node="peer-A")
        reloaded = ExternalCIDLibrary(self.storage, self.kubo).get(reference.reference_id)
        self.assertEqual(reloaded.cid, self.cid)
        self.assertEqual(reloaded.description, "External document")
        self.assertEqual(reloaded.source_node, "peer-A")

    def test_rejects_empty_description_and_unsupported_cid(self):
        with self.assertRaises(ExternalCIDError):
            self.library.add(self.cid, " ")
        with self.assertRaises(ExternalCIDError):
            self.library.add("not-a-cid", "Invalid")

    def test_search_and_update_reference(self):
        reference = self.library.add(self.cid, "Project document", notes="archive")
        self.assertEqual(len(self.library.search("PROJECT")), 1)
        updated = self.library.update(
            reference.reference_id, description="Revised document", notes="current"
        )
        self.assertEqual(updated.description, "Revised document")
        self.assertEqual(updated.notes, "current")

    def test_remove_reference_does_not_unpin_or_delete_content(self):
        reference = self.library.add(self.cid, "Keep CID")
        self.kubo.pin_remove.assert_not_called()
        self.assertTrue(self.library.remove(reference.reference_id))
        self.assertEqual(self.library.list(), [])
        self.kubo.pin_remove.assert_not_called()

    def test_pin_status_uses_kubo_pin_list(self):
        self.kubo.pin_list.return_value = {self.cid: {"Type": "recursive"}}
        self.assertTrue(self.library.is_pinned_locally(self.cid))
        self.kubo.pin_list.return_value = {}
        self.assertFalse(self.library.is_pinned_locally(self.cid))

    def test_pin_and_unpin_delegate_to_kubo(self):
        self.library.pin(self.cid)
        self.kubo.pin_add.assert_called_once_with(self.cid)
        self.library.unpin(self.cid)
        self.kubo.pin_remove.assert_called_once_with(self.cid)

    def test_retrieve_writes_content_returned_by_kubo(self):
        self.kubo.cat.return_value = b"external content"
        destination = Path(self.temporary.name) / "nested" / "content.txt"
        result = self.library.retrieve(self.cid, destination)
        self.assertEqual(result.read_bytes(), b"external content")
        self.kubo.cat.assert_called_once_with(self.cid)

    def test_empty_search_is_rejected(self):
        with self.assertRaises(ExternalCIDError):
            self.library.search("  ")


if __name__ == "__main__":
    unittest.main()
