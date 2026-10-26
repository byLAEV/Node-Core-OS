import unittest

from tools.intent_certificate_simulator import (
    IntentCertificateSimulator,
    build_demo_chain,
    demo_requests,
    signed_certificate,
)


class IntentCertificateSimulatorTests(unittest.TestCase):
    def setUp(self):
        self.certificates = build_demo_chain()
        self.simulator = IntentCertificateSimulator(self.certificates)
        self.valid_request = {
            "request_id": "test-valid",
            "certificate_id": "demo-proof-001",
            "intent": "monitor_availability",
            "resource": "/status",
            "operation": "GET",
            "timestamp": "2026-10-25T12:00:00Z",
        }

    def test_valid_intention_is_allowed(self):
        result = self.simulator.evaluate(self.valid_request)
        self.assertEqual(result.outcome, "ALLOW")
        self.assertEqual(result.reason, "INTENT_SCOPE_AND_CHAIN_VALID")

    def test_scope_escalation_is_denied(self):
        request = {**self.valid_request, "resource": "/admin"}
        result = self.simulator.evaluate(request)
        self.assertEqual(result.outcome, "DENY")
        self.assertEqual(result.reason, "REQUEST_OUTSIDE_CERTIFICATE_SCOPE")

    def test_operation_mismatch_is_denied(self):
        request = {**self.valid_request, "operation": "POST"}
        result = self.simulator.evaluate(request)
        self.assertEqual(result.outcome, "DENY")
        self.assertEqual(result.reason, "REQUEST_OUTSIDE_CERTIFICATE_SCOPE")

    def test_declared_intent_mismatch_is_denied(self):
        request = {**self.valid_request, "intent": "bulk_download"}
        result = self.simulator.evaluate(request)
        self.assertEqual(result.reason, "INTENT_MISMATCH")

    def test_revoked_certificate_is_denied(self):
        simulator = IntentCertificateSimulator(self.certificates, revoked={"demo-proof-001"})
        result = simulator.evaluate(self.valid_request)
        self.assertEqual(result.reason, "CERTIFICATE_REVOKED")

    def test_suspect_certificate_is_restricted_not_revoked(self):
        simulator = IntentCertificateSimulator(self.certificates, suspect={"demo-proof-001"})
        result = simulator.evaluate(self.valid_request)
        self.assertEqual(result.outcome, "ALLOW_RESTRICTED")
        self.assertEqual(result.reason, "SUSPECT_CERTIFICATE_RESTRICTED")

    def test_suspect_write_operation_outside_scope_is_denied(self):
        simulator = IntentCertificateSimulator(self.certificates, suspect={"demo-proof-001"})
        request = {**self.valid_request, "operation": "POST"}
        result = simulator.evaluate(request)
        self.assertEqual(result.outcome, "DENY")
        self.assertEqual(result.reason, "REQUEST_OUTSIDE_CERTIFICATE_SCOPE")

    def test_invalid_signature_is_denied(self):
        self.certificates["demo-proof-001"]["intent"] = "altered_intent"
        result = self.simulator.evaluate(self.valid_request)
        self.assertEqual(result.reason, "INVALID_SIGNATURE")

    def test_expired_certificate_is_denied(self):
        request = {**self.valid_request, "timestamp": "2026-12-02T00:00:00Z"}
        result = self.simulator.evaluate(request)
        self.assertEqual(result.reason, "CERTIFICATE_EXPIRED")

    def test_rate_limit_is_enforced(self):
        results = [
            self.simulator.evaluate(item)
            for item in demo_requests()
            if item["resource"] == "/status" and item["operation"] == "GET"
        ]
        self.assertEqual([r.outcome for r in results], ["ALLOW", "ALLOW", "ALLOW", "LIMIT"])
        self.assertEqual(results[-1].reason, "REQUEST_RATE_LIMIT_EXCEEDED")

    def test_metrics_count_outcomes(self):
        self.simulator.evaluate(self.valid_request)
        metrics = self.simulator.metrics()
        self.assertEqual(metrics["total_requests"], 1)
        self.assertEqual(metrics["outcomes"]["ALLOW"], 1)

    def test_child_scope_cannot_exceed_parent(self):
        altered = self.certificates["demo-proof-001"].copy()
        altered.pop("signature")
        altered["scope"] = {"resources": ["/admin"], "operations": ["GET"]}
        self.certificates["demo-proof-001"] = signed_certificate(**altered)
        result = self.simulator.evaluate(self.valid_request)
        self.assertEqual(result.reason, "CHILD_SCOPE_EXCEEDS_PARENT")


if __name__ == "__main__":
    unittest.main()
