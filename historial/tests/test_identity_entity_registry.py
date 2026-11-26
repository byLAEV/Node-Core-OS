import json
import os
from pathlib import Path
import tempfile
import unittest

from node_core.identity.entity_registry import (
    EntityIdentityRegistry,
    EntityIdentityRegistryError,
)


class EntityIdentityRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.registry = EntityIdentityRegistry(self.root)

    def test_registers_person_without_document_requirement(self):
        entity = self.registry.register_entity("person")
        self.assertEqual(entity["entity_type"], "person")
        self.assertEqual(entity["identity_assurance"], "declared")
        self.assertIsNone(entity["display_name"])
        self.assertEqual(entity["node_links"], [])
        self.assertEqual(entity["evidence_references"], [])

    def test_supports_non_person_entities(self):
        for entity_type in ("organization", "device", "object", "service", "program", "resource"):
            self.registry.register_entity(entity_type)
        self.assertEqual(len(self.registry.list_entities()), 6)

    def test_rejects_unknown_entity_type(self):
        with self.assertRaises(EntityIdentityRegistryError):
            self.registry.register_entity("passport")

    def test_one_entity_can_link_multiple_nodes(self):
        entity = self.registry.register_entity("person")
        self.registry.link_node(entity["entity_id"], "sha256:node-a", relationship="controlled_by")
        updated = self.registry.link_node(
            entity["entity_id"], "sha256:node-b", relationship="controlled_by"
        )
        self.assertEqual(len(updated["node_links"]), 2)
        self.assertEqual(
            {item["node_id"] for item in updated["node_links"]},
            {"sha256:node-a", "sha256:node-b"},
        )

    def test_same_node_relationship_is_idempotent(self):
        entity = self.registry.register_entity("device")
        self.registry.link_node(entity["entity_id"], "node-1")
        self.registry.link_node(entity["entity_id"], "node-1")
        self.assertEqual(len(self.registry.get_entity(entity["entity_id"])["node_links"]), 1)

    def test_node_link_is_explicitly_unverified(self):
        entity = self.registry.register_entity("person")
        updated = self.registry.link_node(entity["entity_id"], "node-1")
        self.assertEqual(updated["node_links"][0]["status"], "declared")

    def test_unlink_removes_only_matching_relationship(self):
        entity = self.registry.register_entity("organization")
        self.registry.link_node(entity["entity_id"], "node-1", relationship="operated_by")
        self.registry.link_node(entity["entity_id"], "node-1", relationship="serves")
        updated = self.registry.unlink_node(
            entity["entity_id"], "node-1", relationship="operated_by"
        )
        self.assertEqual(len(updated["node_links"]), 1)
        self.assertEqual(updated["node_links"][0]["relationship"], "serves")

    def test_evidence_stores_reference_not_raw_document(self):
        entity = self.registry.register_entity("person")
        updated = self.registry.add_evidence_reference(
            entity["entity_id"],
            "identity_document",
            "local-evidence://document-record-001",
            issuer_reference="issuer:example",
        )
        evidence = updated["evidence_references"][0]
        self.assertEqual(evidence["verification_status"], "unverified")
        self.assertNotIn("document_number", evidence)
        self.assertEqual(evidence["reference"], "local-evidence://document-record-001")

    def test_entity_can_be_revoked_without_deleting_audit_record(self):
        entity = self.registry.register_entity("service")
        revoked = self.registry.revoke_entity(entity["entity_id"])
        self.assertEqual(revoked["status"], "revoked")
        self.assertIsNotNone(revoked["revoked_at"])
        self.assertEqual(self.registry.get_entity(entity["entity_id"])["status"], "revoked")

    def test_revoked_entity_cannot_receive_new_node_link(self):
        entity = self.registry.register_entity("object")
        self.registry.revoke_entity(entity["entity_id"])
        with self.assertRaises(EntityIdentityRegistryError):
            self.registry.link_node(entity["entity_id"], "node-1")

    def test_unknown_entity_fails(self):
        with self.assertRaises(EntityIdentityRegistryError):
            self.registry.get_entity("missing")

    def test_corrupt_registry_fails_closed(self):
        entity = self.registry.register_entity("person")
        self.registry.path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(EntityIdentityRegistryError):
            self.registry.get_entity(entity["entity_id"])

    def test_registry_file_permissions_are_restrictive_on_posix(self):
        self.registry.register_entity("program")
        if os.name == "posix":
            self.assertEqual(self.registry.path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.registry.identity_dir.stat().st_mode & 0o777, 0o700)

    def test_returns_copies_not_mutable_internal_state(self):
        entity = self.registry.register_entity("device")
        entity["node_links"].append({"node_id": "forged"})
        self.assertEqual(self.registry.get_entity(entity["entity_id"])["node_links"], [])


if __name__ == "__main__":
    unittest.main()
