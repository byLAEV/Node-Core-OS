"""Local tests for opaque CID intent-lobby tickets."""
import unittest

from node_core.security.cdd_intent import (
    CDDIntentError,
    CDDIntentLobby,
    IntentRoute,
)


class CDDIntentLobbyTests(unittest.TestCase):
    def setUp(self):
        self.now = [100.0]
        self.counter = [0]

        def token_factory():
            self.counter[0] += 1
            return f"opaque-intent-ticket-{self.counter[0]:040d}"

        self.lobby = CDDIntentLobby(
            {
                "read-document": IntentRoute(
                    destination_id="web2:docs",
                    content_cid="bafybeigdyrzt5sfp7udm7hu76uh4d3g5q4m3f4j2q",
                ),
                "account-login": IntentRoute(
                    destination_id="web2:account",
                    content_cid="bafybeigdyrzt5sfp7udm7hu76uh4d3g5q4m3f4j2q",
                ),
            },
            max_active_tickets=2,
            clock=lambda: self.now[0],
            token_factory=token_factory,
        )

    def test_issue_and_consume_returns_internal_route_not_cid_in_handle(self):
        handle = self.lobby.issue("read-document", min_wait_seconds=3)
        self.assertNotIn("bafy", handle)
        self.now[0] += 3
        grant = self.lobby.consume(handle)
        self.assertEqual(grant.intent, "read-document")
        self.assertEqual(grant.destination_id, "web2:docs")
        self.assertIn("bafy", grant.content_cid)

    def test_early_consume_does_not_consume_ticket(self):
        handle = self.lobby.issue("read-document", min_wait_seconds=3)
        with self.assertRaisesRegex(CDDIntentError, "minimum wait"):
            self.lobby.consume(handle)
        self.now[0] += 3
        self.assertEqual(self.lobby.consume(handle).intent, "read-document")

    def test_ticket_is_single_use(self):
        handle = self.lobby.issue("account-login", min_wait_seconds=0)
        self.lobby.consume(handle)
        with self.assertRaisesRegex(CDDIntentError, "unknown, expired, or already used"):
            self.lobby.consume(handle)

    def test_unknown_intent_is_rejected(self):
        with self.assertRaisesRegex(CDDIntentError, "not registered"):
            self.lobby.issue("https://attacker.example/redirect", min_wait_seconds=0)

    def test_expired_ticket_is_rejected(self):
        handle = self.lobby.issue("read-document", ttl_seconds=5, min_wait_seconds=0)
        self.now[0] += 5
        with self.assertRaisesRegex(CDDIntentError, "unknown, expired, or already used"):
            self.lobby.consume(handle)

    def test_active_ticket_table_is_bounded(self):
        self.lobby.issue("read-document", min_wait_seconds=0)
        self.lobby.issue("account-login", min_wait_seconds=0)
        with self.assertRaisesRegex(CDDIntentError, "at capacity"):
            self.lobby.issue("read-document", min_wait_seconds=0)

    def test_bad_configuration_and_limits_are_rejected(self):
        with self.assertRaises(ValueError):
            CDDIntentLobby({})
        with self.assertRaises(CDDIntentError):
            self.lobby.issue("read-document", ttl_seconds=901, min_wait_seconds=0)
        with self.assertRaises(CDDIntentError):
            self.lobby.issue("read-document", ttl_seconds=10, min_wait_seconds=11)


if __name__ == "__main__":
    unittest.main()
