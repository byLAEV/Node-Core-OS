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
            birth_date="1990-05-12",
            height_cm=178,
            gender="Man",
        )

    def test_profile_is_saved_locally_and_marked_declared(self):
        profile = self.save_sample()
        self.assertTrue(self.store.profile_path.is_file())
        self.assertEqual(profile["identity_status"], "declared")
        self.assertEqual(profile["full_name"], "Sample Person")
        self.assertEqual(profile["birth_date"], "1990-05-12")
        self.assertEqual(profile["height_cm"], 178)
        self.assertEqual(profile["gender"], "Man")
        self.assertTrue(profile["created_at"].endswith("+00:00"))
        self.assertTrue(profile["updated_at"].endswith("+00:00"))
        self.assertIsNone(profile["node_id"])
        stored = json.loads(self.store.profile_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["document_number"], "SYNTHETIC-TEST-0001")

    def test_edit_preserves_logical_identity_and_node_association(self):
        original = self.save_sample()
        self.store.associate_node("12D3KooWExamplePeerId")
        updated = self.store.save_declared_profile(
            full_name="Sample Person Updated",
            document_number="SYNTHETIC-TEST-0002",
        )
        self.assertEqual(updated["identity_id"], original["identity_id"])
        self.assertEqual(updated["node_id"], "12D3KooWExamplePeerId")
        self.assertEqual(updated["full_name"], "Sample Person Updated")
        self.assertEqual(updated["birth_date"], "1990-05-12")
        self.assertEqual(updated["height_cm"], 178)
        self.assertEqual(updated["gender"], "Man")
        self.assertEqual(updated["created_at"], original["created_at"])
        self.assertGreaterEqual(updated["updated_at"], original["updated_at"])

    def test_optional_fields_can_be_cleared_explicitly(self):
        self.save_sample()
        updated = self.store.save_declared_profile(
            birth_date="",
            height_cm="",
            gender="",
        )
        self.assertEqual(updated["birth_date"], "")
        self.assertIsNone(updated["height_cm"])
        self.assertEqual(updated["gender"], "")

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

    def test_main_menu_shows_all_saved_identity_values_and_consensus_status(self):
        profile = self.save_sample()
        self.store.associate_node("12D3KooWExamplePeerId")
        menu = MainMenu(SimpleNamespace(identity_profile=self.store))
        output = StringIO()
        with redirect_stdout(output):
            menu._print_identity_summary()
        displayed = output.getvalue()
        self.assertIn("Sample Person", displayed)
        self.assertIn("Alias: SAMPLE", displayed)
        self.assertIn("Nationality: Costa Rican", displayed)
        self.assertIn("Issuing country: Costa Rica", displayed)
        self.assertIn("Document type: National identity document", displayed)
        self.assertIn("Document number: SYNTHETIC-TEST-0001", displayed)
        self.assertIn("Date of birth: 1990-05-12", displayed)
        self.assertIn("Height: 178 cm", displayed)
        self.assertIn("Gender: Man", displayed)
        self.assertIn(f"Identity data first entered (UTC): {profile['created_at']}", displayed)
        self.assertIn(f"Identity data last updated (UTC): {profile['updated_at']}", displayed)
        self.assertIn(f"Logical identity ID: {profile['identity_id']}", displayed)
        self.assertIn("12D3KooWExamplePeerId", displayed)
        self.assertIn("Identity data status: Declared", displayed)
        self.assertIn("Node Core OS network consensus verification: Not verified", displayed)

    def test_invalid_birth_date_and_height_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.save_declared_profile(
                full_name="Sample Person",
                alias="",
                nationality="",
                issuing_country="Costa Rica",
                document_type="National identity document",
                document_number="SYNTHETIC-TEST-0001",
                birth_date="2035-01-01",
            )
        with self.assertRaises(ValueError):
            self.store.save_declared_profile(
                full_name="Sample Person",
                alias="",
                nationality="",
                issuing_country="Costa Rica",
                document_type="National identity document",
                document_number="SYNTHETIC-TEST-0001",
                height_cm="not-a-number",
            )

    def test_profile_file_permissions_are_private_where_supported(self):
        self.save_sample()
        if hasattr(self.store.profile_path.stat(), "st_mode"):
            mode = self.store.profile_path.stat().st_mode & 0o777
            if mode != 0:
                self.assertEqual(mode, 0o600)


if __name__ == "__main__":
    unittest.main()
