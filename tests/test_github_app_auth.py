"""Tests for GitHub App device authorization and installation tokens."""
from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from node_core.github_app_auth import GitHubAppAuth, GitHubAppError


class GitHubAppAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.auth = GitHubAppAuth(Path(self.temp.name))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_start_device_flow_saves_pending_code_and_returns_user_instructions(self) -> None:
        response = {
            "device_code": "device-secret",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        }
        with patch.object(GitHubAppAuth, "_post_form", return_value=response):
            result = self.auth.start_device_flow("Iv1.example")
        self.assertEqual(result["state"], "pending")
        self.assertEqual(result["user_code"], "ABCD-1234")
        saved = json.loads(self.auth.pending_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["device_code"], "device-secret")

    def test_poll_pending_respects_poll_interval_without_network(self) -> None:
        with patch.object(GitHubAppAuth, "_post_form", return_value={
            "device_code": "device", "user_code": "ABCD", "verification_uri": "https://github.com/login/device",
            "expires_in": 900, "interval": 5,
        }), patch("node_core.github_app_auth.time.time", return_value=100):
            self.auth.start_device_flow("client")
        with patch("node_core.github_app_auth.time.time", return_value=102), patch.object(
            GitHubAppAuth, "_post_form", side_effect=AssertionError("polling too early")
        ):
            result = self.auth.poll_device_flow()
        self.assertEqual(result["state"], "pending")
        self.assertEqual(result["wait_seconds"], 3)

    def test_poll_authorized_saves_operator_and_removes_pending_code(self) -> None:
        with patch.object(GitHubAppAuth, "_post_form", return_value={
            "device_code": "device", "user_code": "ABCD", "verification_uri": "https://github.com/login/device",
            "expires_in": 900, "interval": 1,
        }), patch("node_core.github_app_auth.time.time", return_value=100):
            self.auth.start_device_flow("client")
        with patch("node_core.github_app_auth.time.time", return_value=102), patch.object(
            GitHubAppAuth, "_post_form", return_value={
                "access_token": "user-token", "refresh_token": "refresh-token",
                "expires_in": 28800, "refresh_token_expires_in": 15552000,
            }
        ), patch.object(GitHubAppAuth, "_get_json", return_value={"login": "octocat"}):
            result = self.auth.poll_device_flow("octocat")
        self.assertEqual(result["state"], "authorized")
        self.assertEqual(result["github_login"], "octocat")
        self.assertFalse(self.auth.pending_path.exists())
        saved = json.loads(self.auth.operator_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["access_token"], "user-token")
        self.assertEqual(self.auth.operator_path.stat().st_mode & 0o777, 0o600)

    def test_poll_rejects_account_that_does_not_match_expected_operator(self) -> None:
        with patch.object(GitHubAppAuth, "_post_form", return_value={
            "device_code": "device", "user_code": "ABCD", "verification_uri": "https://github.com/login/device",
            "expires_in": 900, "interval": 1,
        }), patch("node_core.github_app_auth.time.time", return_value=100):
            self.auth.start_device_flow("client")
        with patch("node_core.github_app_auth.time.time", return_value=102), patch.object(
            GitHubAppAuth, "_post_form", return_value={"access_token": "token"}
        ), patch.object(GitHubAppAuth, "_get_json", return_value={"login": "other"}):
            with self.assertRaisesRegex(GitHubAppError, "does not match"):
                self.auth.poll_device_flow("octocat")
        self.assertFalse(self.auth.operator_path.exists())

    def test_expired_device_code_is_removed(self) -> None:
        with patch.object(GitHubAppAuth, "_post_form", return_value={
            "device_code": "device", "user_code": "ABCD", "verification_uri": "https://github.com/login/device",
            "expires_in": 10, "interval": 1,
        }), patch("node_core.github_app_auth.time.time", return_value=100):
            self.auth.start_device_flow("client")
        with patch("node_core.github_app_auth.time.time", return_value=111):
            result = self.auth.poll_device_flow()
        self.assertEqual(result["state"], "expired")
        self.assertFalse(self.auth.pending_path.exists())

    def test_app_jwt_contains_expected_issuer_and_short_expiration(self) -> None:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        path = Path(self.temp.name) / "app.pem"
        path.write_bytes(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))
        token = self.auth._create_app_jwt("12345", path)
        header, payload, signature = token.split(".")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        self.assertEqual(claims["iss"], "12345")
        self.assertLessEqual(claims["exp"] - claims["iat"], 600)
        self.assertEqual(json.loads(base64.urlsafe_b64decode(header + "=" * (-len(header) % 4)))["alg"], "RS256")
        self.assertTrue(signature)


if __name__ == "__main__":
    unittest.main()
