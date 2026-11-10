"""Regression tests for evidence-gated Node Core OS 2.0 readiness."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_release_2_0", ROOT / "scripts" / "audit_release_2_0.py"
)
AUDIT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(AUDIT)


class ReadinessEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "release").mkdir()
        self.contract_path = self.root / "release" / "readiness.json"
        self.artifact = self.root / "evidence" / "acceptance.txt"
        self.artifact.parent.mkdir()
        self.artifact.write_text("verified test evidence\n", encoding="utf-8")
        self.data = {
            "schema_version": 1,
            "release": "2.0.0",
            "source_branch": "main",
            "requirements": {key: False for key in AUDIT.EXPECTED_REQUIREMENTS},
            "evidence": {},
        }

    def tearDown(self):
        self.temp.cleanup()

    def write_contract(self):
        self.contract_path.write_text(json.dumps(self.data), encoding="utf-8")

    def approve_with_evidence(self, key):
        self.data["requirements"][key] = True
        self.data["evidence"][key] = {
            "artifact": "evidence/acceptance.txt",
            "sha256": hashlib.sha256(self.artifact.read_bytes()).hexdigest(),
        }

    def test_approved_requirement_without_evidence_is_rejected(self):
        key = sorted(AUDIT.EXPECTED_REQUIREMENTS)[0]
        self.data["requirements"][key] = True
        self.write_contract()
        with self.assertRaisesRegex(ValueError, "lacks an artifact path"):
            AUDIT.load_contract(self.contract_path)

    def test_approved_requirement_with_matching_sha256_is_accepted(self):
        key = sorted(AUDIT.EXPECTED_REQUIREMENTS)[0]
        self.approve_with_evidence(key)
        self.write_contract()
        loaded = AUDIT.load_contract(self.contract_path)
        self.assertTrue(loaded["requirements"][key])

    def test_tampered_evidence_is_rejected(self):
        key = sorted(AUDIT.EXPECTED_REQUIREMENTS)[0]
        self.approve_with_evidence(key)
        self.artifact.write_text("tampered\n", encoding="utf-8")
        self.write_contract()
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            AUDIT.load_contract(self.contract_path)

    def test_path_traversal_is_rejected(self):
        key = sorted(AUDIT.EXPECTED_REQUIREMENTS)[0]
        self.approve_with_evidence(key)
        self.data["evidence"][key]["artifact"] = "../outside.txt"
        self.write_contract()
        with self.assertRaisesRegex(ValueError, "normalized relative path"):
            AUDIT.load_contract(self.contract_path)

    def test_symlink_evidence_is_rejected(self):
        key = sorted(AUDIT.EXPECTED_REQUIREMENTS)[0]
        link = self.root / "evidence" / "linked.txt"
        link.symlink_to(self.artifact)
        self.data["requirements"][key] = True
        self.data["evidence"][key] = {
            "artifact": "evidence/linked.txt",
            "sha256": hashlib.sha256(self.artifact.read_bytes()).hexdigest(),
        }
        self.write_contract()
        with self.assertRaisesRegex(ValueError, "contains a symlink"):
            AUDIT.load_contract(self.contract_path)


if __name__ == "__main__":
    unittest.main()
