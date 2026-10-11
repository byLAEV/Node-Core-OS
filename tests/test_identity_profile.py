import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from node_core.ui import MainMenu

from node_core.identity.profile import IdentityProfileStore


class IdentityProfileStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.store = IdentityProfileStore(self.root)

    def save_sample(self):
        return self.store.save_declared_profile(
            full_name="Sample Person",
            alias="SAMPLE",
            nationality="Costa Rican",
            issuing_country="Costa Rica",
            document_type="National identity document",
            document_number="SYNTHETIC-TEST-0001",
        )

    def test_profile_is_saved_locally_and_marked_declared(self):
        profile = self.save_sample()
        self.assertTrue(self.store.profile_path.is_file())
        self.assertEqual(profile["identity_status"], "declared")
        self.assertEqual(profile["full_name"], "Sample Person")
        self.assertIsNone(profile["node_id"])
        stored = json.loads(self.store.profile_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["document_number"], "SYNTHETIC-TEST-0001")

    def test_edit_preserves_logical_identity_and_node_association(self):
        original = self.save_sample()
        self.store.associate_node("12D3KooWExamplePeerId")
        updated = self.store.save_declared_profile(
            full_name="Sample Person Updated",
            alias="SAMPLE",
            nationality="Costa Rican",
            issuing_country="Costa Rica",
            document_type="National identity document",
            document_number="SYNTHETIC-TEST-0002",
        )
        self.assertEqual(updated["identity_id"], original["identity_id"])
        self.assertEqual(updated["node_id"], "12D3KooWExamplePeerId")
        self.assertEqual(updated["full_name"], "Sample Person Updated")

    def test_association_requires_profile_and_nonempty_node_id(self):
        with self.assertRaises(ValueError):
            self.store.associate_node("12D3KooWExamplePeerId")
        self.save_sample()
        with self.assertRaises(ValueError):
            self.store.associate_node("  ")

    def test_required_fields_are_validated(self):
        with self.assertRaises(ValueError):
            self.store.save_declared_profile(
                full_name=" ",
                alias="",
                nationality="",
                issuing_country="Costa Rica",
                document_type="National identity document",
                document_number="SYNTHETIC-TEST-0001",
            )

    def test_main_menu_shows_profile_without_document_number(self):
        self.save_sample()
        self.store.associate_node("12D3KooWExamplePeerId")
        menu = MainMenu(SimpleNamespace(identity_profile=self.store))
        output = StringIO()
        with redirect_stdout(output):
            menu._print_identity_summary()
        displayed = output.getvalue()
        self.assertIn("Sample Person", displayed)
        self.assertIn("SAMPLE", displayed)
        self.assertIn("Costa Rican", displayed)
        self.assertIn("12D3KooWExamplePeerId", displayed)
        self.assertIn("Declared (not independently verified)", displayed)
        self.assertNotIn("SYNTHETIC-TEST-0001", displayed)

    def test_profile_file_permissions_are_private_where_supported(self):
        self.save_sample()
        if hasattr(self.store.profile_path.stat(), "st_mode"):
            mode = self.store.profile_path.stat().st_mode & 0o777
            if mode != 0:
                self.assertEqual(mode, 0o600)


if __name__ == "__main__":
    unittest.main()
