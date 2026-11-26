from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:  # Optional test dependency; installed by the BICDN catalog workflow.
    Draft202012Validator = None
    FormatChecker = None


ROOT = Path(__file__).resolve().parents[1]
CERTIFICATE_DIR = (
    ROOT
    / "Catalog of Products and Services as Business Models for the "
    "Node Core OS Identity Node Network by LAEV"
    / "Certificates"
    / "09-bitcoin-conflict-declaration-and-resolution"
)
FORMAT_CHECKER = FormatChecker() if FormatChecker is not None else None


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@unittest.skipIf(
    Draft202012Validator is None,
    "jsonschema is installed by the dedicated BICDN catalog-integrity workflow",
)
class BICDNSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case_schema = load_json(CERTIFICATE_DIR / "bicdn-case.schema.json")
        cls.contribution_schema = load_json(
            CERTIFICATE_DIR / "bicdn-contribution.schema.json"
        )
        cls.case_validator = Draft202012Validator(
            cls.case_schema, format_checker=FORMAT_CHECKER
        )
        cls.contribution_validator = Draft202012Validator(
            cls.contribution_schema, format_checker=FORMAT_CHECKER
        )
        cls.anonymous_legal_request = load_json(
            CERTIFICATE_DIR
            / "examples"
            / "anonymous-legal-contact-request.json"
        )

    def test_schemas_are_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(self.case_schema)
        Draft202012Validator.check_schema(self.contribution_schema)

    def test_anonymous_legal_contact_example_is_valid(self):
        self.contribution_validator.validate(self.anonymous_legal_request)

    def test_private_contribution_requires_encrypted_message_reference(self):
        event = copy.deepcopy(self.anonymous_legal_request)
        event["content"].pop("encrypted_message_reference")
        self.assertTrue(
            list(self.contribution_validator.iter_errors(event)),
            "private contribution without encrypted reference must be rejected",
        )

    def test_public_contribution_does_not_require_encrypted_message_reference(self):
        event = copy.deepcopy(self.anonymous_legal_request)
        event["visibility"]["content"] = "public"
        event["content"].pop("encrypted_message_reference")
        self.contribution_validator.validate(event)

    def test_minimal_case_declaration_is_valid(self):
        case = {
            "schema_version": "1.0.0",
            "product_id": "BICDN-01",
            "profile": "bitcoin-conflict-declaration",
            "case_id": "BICDN-DEMO-2026-000001",
            "created_at": "2026-11-09T18:00:00-06:00",
            "declaration": {
                "category": "other",
                "statement": "Synthetic test declaration.",
            },
            "identity": {
                "mode": "anonymous",
                "assurance": "not_verified",
            },
            "jurisdictions": [],
            "evidence": [],
            "visibility": {
                "case_metadata": "public",
                "declaration": "private",
                "evidence": "private",
            },
            "resolution_access": {"requested": False},
        }
        self.case_validator.validate(case)

    def test_restricted_evidence_requires_encrypted_storage_reference(self):
        case = {
            "schema_version": "1.0.0",
            "product_id": "BICDN-01",
            "profile": "bitcoin-conflict-declaration",
            "case_id": "BICDN-DEMO-2026-000002",
            "created_at": "2026-11-09T18:00:00-06:00",
            "declaration": {
                "category": "other",
                "statement": "Synthetic test declaration.",
            },
            "identity": {
                "mode": "anonymous",
                "assurance": "not_verified",
            },
            "jurisdictions": [],
            "evidence": [
                {
                    "evidence_id": "EVIDENCE-001",
                    "description": "Synthetic restricted evidence.",
                    "classification": "document",
                    "digest": "sha256:" + "a" * 64,
                    "access_policy": "restricted",
                }
            ],
            "visibility": {
                "case_metadata": "public",
                "declaration": "private",
                "evidence": "restricted",
            },
            "resolution_access": {"requested": False},
        }
        self.assertTrue(
            list(self.case_validator.iter_errors(case)),
            "restricted evidence without encrypted reference must be rejected",
        )

    def test_restricted_evidence_with_encrypted_reference_is_valid(self):
        case = {
            "schema_version": "1.0.0",
            "product_id": "BICDN-01",
            "profile": "bitcoin-conflict-declaration",
            "case_id": "BICDN-DEMO-2026-000003",
            "created_at": "2026-11-09T18:00:00-06:00",
            "declaration": {
                "category": "other",
                "statement": "Synthetic test declaration.",
            },
            "identity": {
                "mode": "anonymous",
                "assurance": "not_verified",
            },
            "jurisdictions": [],
            "evidence": [
                {
                    "evidence_id": "EVIDENCE-002",
                    "description": "Synthetic restricted evidence.",
                    "classification": "document",
                    "digest": "sha256:" + "b" * 64,
                    "access_policy": "restricted",
                    "encrypted_storage_reference": "private://test/encrypted-object-002",
                }
            ],
            "visibility": {
                "case_metadata": "public",
                "declaration": "private",
                "evidence": "restricted",
            },
            "resolution_access": {"requested": False},
        }
        self.case_validator.validate(case)

    def test_case_rejects_unrecognized_properties(self):
        case = {
            "schema_version": "1.0.0",
            "product_id": "BICDN-01",
            "profile": "bitcoin-conflict-declaration",
            "case_id": "BICDN-DEMO-2026-000004",
            "created_at": "2026-11-09T18:00:00-06:00",
            "declaration": {
                "category": "other",
                "statement": "Synthetic test declaration.",
            },
            "identity": {
                "mode": "anonymous",
                "assurance": "not_verified",
            },
            "jurisdictions": [],
            "evidence": [],
            "visibility": {
                "case_metadata": "public",
                "declaration": "private",
                "evidence": "private",
            },
            "resolution_access": {"requested": False},
            "unrecognized_field": True,
        }
        self.assertTrue(list(self.case_validator.iter_errors(case)))


if __name__ == "__main__":
    unittest.main()
