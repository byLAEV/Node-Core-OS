import unittest
from datetime import datetime, timedelta, timezone

from node_core.identity.function_proof import (
    EvidenceValidationError,
    derive_evidence_status,
    validate_evidence_record,
)


def valid_record():
    return {
        "schema": "node-core.identity-function-evidence",
        "schema_version": "0.1.0",
        "evidence_id": "evidence-001",
        "identity_ref": "identity-key-001",
        "activity": {
            "protocol_id": "node-core.preferences",
            "poll_id": "poll-001",
            "period_id": "period-001",
            "activity_type": "valid_participation",
        },
        "timestamps": {
            "created_at": "2026-10-09T12:00:00Z",
            "valid_from": "2026-10-09T00:00:00Z",
            "valid_until": "2026-10-16T00:00:00Z",
        },
        "validation": {
            "policy_version": "0.1.0",
            "status": "locally_validated",
            "checks": ["schema", "period"],
        },
        "content": {"cid": None, "previous_evidence_ref": None},
        "signature": {
            "algorithm": "test-placeholder",
            "value": "test-placeholder-not-cryptographically-verified",
        },
    }


class IdentityFunctionProofTests(unittest.TestCase):
    def test_valid_record_passes_structural_validation(self):
        self.assertIsNone(validate_evidence_record(valid_record()))

    def test_unknown_schema_is_rejected(self):
        record = valid_record()
        record["schema"] = "other-schema"
        with self.assertRaises(EvidenceValidationError):
            validate_evidence_record(record)

    def test_missing_activity_reference_is_rejected(self):
        record = valid_record()
        del record["activity"]["poll_id"]
        with self.assertRaises(EvidenceValidationError):
            validate_evidence_record(record)

    def test_timestamp_without_timezone_is_rejected(self):
        record = valid_record()
        record["timestamps"]["created_at"] = "2026-10-09T12:00:00"
        with self.assertRaises(EvidenceValidationError):
            validate_evidence_record(record)

    def test_expiry_must_be_after_valid_from(self):
        record = valid_record()
        record["timestamps"]["valid_until"] = "2026-10-08T00:00:00Z"
        with self.assertRaises(EvidenceValidationError):
            validate_evidence_record(record)

    def test_creation_cannot_precede_validity_start(self):
        record = valid_record()
        record["timestamps"]["created_at"] = "2026-10-08T12:00:00Z"
        with self.assertRaises(EvidenceValidationError):
            validate_evidence_record(record)

    def test_status_current(self):
        status = derive_evidence_status(
            valid_record(),
            now=datetime(2026, 10, 10, tzinfo=timezone.utc),
        )
        self.assertEqual(status, "current")

    def test_status_renewal_due(self):
        status = derive_evidence_status(
            valid_record(),
            now=datetime(2026, 10, 14, tzinfo=timezone.utc),
            renewal_window=timedelta(days=2),
        )
        self.assertEqual(status, "renewal_due")

    def test_status_grace(self):
        status = derive_evidence_status(
            valid_record(),
            now=datetime(2026, 10, 17, tzinfo=timezone.utc),
            grace_period=timedelta(days=2),
        )
        self.assertEqual(status, "grace")

    def test_status_expired_after_grace(self):
        status = derive_evidence_status(
            valid_record(),
            now=datetime(2026, 10, 19, tzinfo=timezone.utc),
            grace_period=timedelta(days=2),
        )
        self.assertEqual(status, "expired")

    def test_future_evidence_is_pending(self):
        status = derive_evidence_status(
            valid_record(),
            now=datetime(2026, 10, 8, tzinfo=timezone.utc),
        )
        self.assertEqual(status, "verification_pending")

    def test_naive_observation_time_is_rejected(self):
        with self.assertRaises(ValueError):
            derive_evidence_status(
                valid_record(),
                now=datetime(2026, 10, 10),
            )

    def test_negative_grace_period_is_rejected(self):
        with self.assertRaises(ValueError):
            derive_evidence_status(
                valid_record(),
                grace_period=timedelta(seconds=-1),
            )


if __name__ == "__main__":
    unittest.main()
