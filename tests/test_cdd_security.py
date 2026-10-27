"""Local-only tests for signed CDD policies and bounded anti-bot rate limiting."""
from datetime import datetime, timedelta, timezone
import tempfile
import unittest
from pathlib import Path

from node_core.identity.node_identity import NodeIdentityStore
from node_core.security.cdd import (
    CDDPolicyError,
    SlidingWindowRateLimiter,
    create_signed_policy,
    verify_signed_policy,
)


class CDDPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="node-core-cdd-")
        self.addCleanup(self.temp.cleanup)
        self.identity = NodeIdentityStore(Path(self.temp.name) / "issuer")
        self.metadata = self.identity.initialize()
        self.trusted = {self.metadata["node_id"]: self.metadata["public_key"]}
        self.now = datetime.now(timezone.utc)

    def make_policy(self, **overrides):
        values = {
            "service_id": "web2:example.test",
            "sequence": 1,
            "issued_at": self.now - timedelta(seconds=1),
            "expires_at": self.now + timedelta(minutes=5),
            "max_requests": 10,
            "window_seconds": 60,
            "max_body_bytes": 8192,
            "origin_id": "origin:example.test",
        }
        values.update(overrides)
        return create_signed_policy(self.identity, **values)

    def test_trusted_unexpired_policy_is_accepted(self):
        policy = self.make_policy()
        self.assertTrue(verify_signed_policy(policy, self.trusted, now=self.now))

    def test_tampered_limits_are_rejected(self):
        policy = self.make_policy()
        policy["limits"]["max_requests"] = 999
        self.assertFalse(verify_signed_policy(policy, self.trusted, now=self.now))

    def test_unknown_issuer_is_rejected(self):
        self.assertFalse(verify_signed_policy(self.make_policy(), {}, now=self.now))

    def test_expired_policy_is_rejected(self):
        policy = self.make_policy(
            issued_at=self.now - timedelta(minutes=10),
            expires_at=self.now - timedelta(minutes=5),
        )
        self.assertFalse(verify_signed_policy(policy, self.trusted, now=self.now))

    def test_future_policy_is_rejected(self):
        policy = self.make_policy(
            issued_at=self.now + timedelta(minutes=1),
            expires_at=self.now + timedelta(minutes=5),
        )
        self.assertFalse(verify_signed_policy(policy, self.trusted, now=self.now))

    def test_rollback_and_replay_sequence_are_rejected(self):
        policy = self.make_policy(sequence=4)
        self.assertFalse(verify_signed_policy(policy, self.trusted, last_sequence=4, now=self.now))
        self.assertFalse(verify_signed_policy(policy, self.trusted, last_sequence=5, now=self.now))

    def test_malformed_signature_and_extra_fields_are_rejected(self):
        policy = self.make_policy()
        policy["signature"] = "not-base64!"
        self.assertFalse(verify_signed_policy(policy, self.trusted, now=self.now))
        policy = self.make_policy()
        policy["unexpected"] = True
        self.assertFalse(verify_signed_policy(policy, self.trusted, now=self.now))

    def test_invalid_policy_limits_are_rejected_at_creation(self):
        for field, value in (
            ("max_requests", 0),
            ("window_seconds", 3601),
            ("max_body_bytes", 1_048_577),
        ):
            with self.subTest(field=field):
                with self.assertRaises(CDDPolicyError):
                    self.make_policy(**{field: value})

    def test_naive_timestamps_are_rejected(self):
        with self.assertRaises(CDDPolicyError):
            self.make_policy(issued_at=datetime(2026, 1, 1), expires_at=self.now + timedelta(days=1))


class CDDRateLimiterTests(unittest.TestCase):
    def setUp(self):
        self.limiter = SlidingWindowRateLimiter()
        self.now = 100.0

    def test_allows_requests_until_quota_then_limits(self):
        results = [
            self.limiter.allow("authenticated-node-a", "/login", max_requests=2,
                               window_seconds=10, now=self.now + offset)
            for offset in (0, 1, 2)
        ]
        self.assertEqual(results, [True, True, False])

    def test_route_and_client_quotas_are_separate(self):
        self.assertTrue(self.limiter.allow("client-a", "/one", max_requests=1,
                                           window_seconds=10, now=self.now))
        self.assertTrue(self.limiter.allow("client-a", "/two", max_requests=1,
                                           window_seconds=10, now=self.now))
        self.assertTrue(self.limiter.allow("client-b", "/one", max_requests=1,
                                           window_seconds=10, now=self.now))

    def test_expired_requests_leave_the_window(self):
        self.assertTrue(self.limiter.allow("client-a", "/route", max_requests=1,
                                           window_seconds=5, now=10.0))
        self.assertTrue(self.limiter.allow("client-a", "/route", max_requests=1,
                                           window_seconds=5, now=15.1))

    def test_tracking_table_is_bounded_and_fails_closed(self):
        limiter = SlidingWindowRateLimiter(max_tracked_clients=1)
        self.assertTrue(limiter.allow("client-a", "/route", max_requests=5,
                                      window_seconds=60, now=1.0))
        self.assertFalse(limiter.allow("client-b", "/route", max_requests=5,
                                       window_seconds=60, now=1.0))

    def test_invalid_client_and_route_are_denied(self):
        self.assertFalse(self.limiter.allow("", "/route", max_requests=5,
                                            window_seconds=60, now=self.now))
        self.assertFalse(self.limiter.allow("client", "route-without-slash",
                                            max_requests=5, window_seconds=60, now=self.now))


if __name__ == "__main__":
    unittest.main()
