import json
import tempfile
import unittest
from pathlib import Path

from node_core.identity.github_pool import (
    GitHubIdentityPool,
    GitHubIdentityPoolError,
)


class GitHubIdentityPoolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pool = GitHubIdentityPool(self.root / ".node-core")
        self.initial = self.pool.initialize("sha256:" + "a" * 64)

    def test_initializes_private_pool_and_encryption_key(self):
        self.assertTrue(Path(self.initial["private_key_path"]).is_file())
        self.assertEqual(
            Path(self.initial["private_key_path"]).stat().st_mode & 0o777,
            0o600,
        )
        self.assertEqual(self.initial["node_count"], 0)
        self.assertEqual(self.pool.public_encryption_key()["algorithm"], "RSA-OAEP-256 + AES-256-GCM")

    def test_reinitialization_preserves_pool_and_key(self):
        private_path = Path(self.initial["private_key_path"])
        before = private_path.read_bytes()
        again = self.pool.initialize("sha256:" + "a" * 64)
        self.assertEqual(before, private_path.read_bytes())
        self.assertEqual(again["pool_id"], self.initial["pool_id"])

    def test_rejects_different_admin_node(self):
        with self.assertRaisesRegex(GitHubIdentityPoolError, "different administrator"):
            self.pool.initialize("sha256:" + "b" * 64)

    def test_adds_only_github_owned_repositories_as_pending(self):
        member = self.pool.add_node("octocat", "octocat/node-core-client")
        self.assertEqual(member["status"], "pending_admin_verification")
        self.assertEqual(member["verification_status"], "not_verified")
        self.assertEqual(self.pool.list_nodes(), [member])

    def test_rejects_repository_owner_mismatch_and_non_github_url(self):
        with self.assertRaisesRegex(GitHubIdentityPoolError, "owner must match"):
            self.pool.add_node("octocat", "somebody-else/node-core-client")
        with self.assertRaises(GitHubIdentityPoolError):
            self.pool.add_node("not a login", "not a login/client")

    def test_duplicate_github_account_cannot_claim_another_repository(self):
        self.pool.add_node("octocat", "octocat/node-core-client")
        with self.assertRaisesRegex(GitHubIdentityPoolError, "already registered"):
            self.pool.add_node("octocat", "octocat/another-client")

    def test_revokes_member_without_deleting_audit_record(self):
        member = self.pool.add_node("octocat", "octocat/node-core-client")
        revoked = self.pool.revoke_node(member["member_id"])
        self.assertEqual(revoked["status"], "revoked")
        self.assertEqual(self.pool.list_nodes()[0]["status"], "revoked")

    def test_encrypts_then_decrypts_personal_record_and_keeps_public_replica_ciphertext_only(self):
        envelope = self.pool.encrypt_record(
            {"full_name": "Synthetic Test Person", "contact_email": "test@example.invalid"},
            consent_given=True,
        )
        result = self.pool.ingest_envelope(envelope, owner_login="octocat")
        self.assertTrue(result["created"])
        private_record = json.loads(Path(result["private_record_path"]).read_text(encoding="utf-8"))
        self.assertEqual(private_record["fields"]["full_name"], "Synthetic Test Person")
        encrypted = Path(result["encrypted_replica_path"]).read_text(encoding="utf-8")
        self.assertNotIn("Synthetic Test Person", encrypted)
        self.assertNotIn("test@example.invalid", encrypted)
        self.assertEqual(result["ciphertext_sha256"], __import__("hashlib").sha256(
            json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest())

    def test_rejects_missing_consent_and_mismatched_encryption_key(self):
        with self.assertRaisesRegex(GitHubIdentityPoolError, "consent"):
            self.pool.encrypt_record({"full_name": "Test"}, consent_given=False)
        envelope = self.pool.encrypt_record({"full_name": "Test"}, consent_given=True)
        envelope["encryption_key_id"] = "0" * 64
        with self.assertRaisesRegex(GitHubIdentityPoolError, "different node"):
            self.pool.ingest_envelope(envelope)

    def test_rejects_tampered_ciphertext(self):
        envelope = self.pool.encrypt_record({"full_name": "Test"}, consent_given=True)
        envelope["ciphertext"] = envelope["ciphertext"][:-4] + "AAAA"
        with self.assertRaisesRegex(GitHubIdentityPoolError, "authenticated decryption"):
            self.pool.ingest_envelope(envelope)

    def test_member_must_export_pages_client_from_its_own_node(self):
        member = self.pool.add_node("octocat", "octocat/node-core-client")
        with self.assertRaisesRegex(GitHubIdentityPoolError, "own Node Core node"):
            self.pool.export_member_client_package(
                member["member_id"], self.root / "exported-client"
            )

    def test_exports_operator_client_with_https_node_binding(self):
        self.pool.configure_local_client(
            "hubot", "hubot/node-core-client",
            node_api_url="https://node.example.test",
        )
        target = self.pool.export_client_package(self.root / "operator-client")
        config = json.loads((target / "node-core-client.json").read_text(encoding="utf-8"))
        self.assertEqual(config["github_account"], "hubot")
        self.assertEqual(config["repository"], "hubot/node-core-client")
        self.assertEqual(config["node_id"], "sha256:" + "a" * 64)
        self.assertEqual(config["node_api_url"], "https://node.example.test")
        self.assertTrue((target / "index.html").is_file())
        self.assertTrue((target / "assets" / "app.js").is_file())

    def test_static_pages_client_posts_to_node_api_without_github_write_token(self):
        client_root = Path(__file__).resolve().parents[1] / "client-template"
        app = (client_root / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertIn("config.node_api_url", app)
        self.assertIn("/api/github/records", app)
        self.assertNotIn("Authorization", app)
        self.assertNotIn("personal access token", app.lower())

    def test_configure_local_client_rejects_http_node_api(self):
        with self.assertRaisesRegex(GitHubIdentityPoolError, "HTTPS"):
            self.pool.configure_local_client(
                "hubot", "hubot/client", node_api_url="http://node.example.test"
            )

    def test_export_refuses_revoked_member_and_requires_member_owned_node(self):
        member = self.pool.add_node("octocat", "octocat/node-core-client")
        self.pool.revoke_node(member["member_id"])
        with self.assertRaisesRegex(GitHubIdentityPoolError, "not found"):
            self.pool.export_member_client_package(member["member_id"], self.root / "revoked")
        active = self.pool.add_node("hubot", "hubot/node-core-client")
        with self.assertRaisesRegex(GitHubIdentityPoolError, "own Node Core node"):
            self.pool.export_member_client_package(active["member_id"], self.root / "member")


if __name__ == "__main__":
    unittest.main()
