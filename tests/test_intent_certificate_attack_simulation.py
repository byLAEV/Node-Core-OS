import unittest

from tools.intent_certificate_attack_simulation import run_attack_simulation


class IntentCertificateAttackSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_attack_simulation()
        cls.by_id = {item["id"]: item for item in cls.report["scenarios"]}

    def test_report_is_explicitly_local_and_synthetic(self):
        self.assertFalse(self.report["live_network_access"])
        self.assertEqual(self.report["mode"], "LOCAL_SYNTHETIC_ATTACK_SIMULATION")

    def test_scope_escalation_is_denied(self):
        self.assertTrue(self.by_id["A1_SCOPE_ESCALATION"]["contained"])

    def test_tampered_certificate_is_denied(self):
        self.assertTrue(self.by_id["A2_CERTIFICATE_TAMPERING"]["contained"])

    def test_revoked_certificate_is_denied(self):
        self.assertTrue(self.by_id["A3_REVOKED_CERTIFICATE"]["contained"])

    def test_false_intent_is_not_semantically_verified(self):
        self.assertFalse(self.by_id["A4_FALSE_BUT_MATCHING_INTENT"]["contained"])

    def test_many_valid_certificates_bypass_aggregate_limit(self):
        scenario = self.by_id["A5_DISTRIBUTED_MANY_CERTIFICATES"]
        self.assertEqual(scenario["observed_allowed"], 60)
        self.assertFalse(scenario["contained"])

    def test_local_node_counters_do_not_coordinate(self):
        scenario = self.by_id["A6_MULTI_NODE_COUNTER_SPLIT"]
        self.assertEqual(scenario["observed_allowed"], 6)
        self.assertFalse(scenario["contained"])

    def test_replay_has_no_dedicated_protection(self):
        scenario = self.by_id["A7_REPLAY_SAME_REQUEST"]
        self.assertEqual(scenario["observed_allowed"], 3)
        self.assertFalse(scenario["contained"])

    def test_suspicion_is_not_propagated(self):
        self.assertFalse(self.by_id["A8_SUSPICION_NOT_PROPAGATED"]["contained"])

    def test_malformed_input_is_not_handled_safely(self):
        self.assertFalse(self.by_id["A9_MALFORMED_REQUEST"]["contained"])

    def test_report_does_not_claim_readiness(self):
        self.assertEqual(self.report["overall_result"], "NOT_READY_FOR_COORDINATED_ATTACK_DEFENSE")
        self.assertGreater(self.report["scenarios_with_gaps"], 0)


if __name__ == "__main__":
    unittest.main()
