"""Tests for GitHub App device authorization and installation tokens."""
from __future__ import annotations
import base64, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from node_core.github_app_auth import GitHubAppAuth, GitHubAppError

class GitHubAppAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.auth=GitHubAppAuth(Path(self.temp.name))
    def tearDown(self): self.temp.cleanup()
    def test_start_device_flow_saves_pending_code(self):
        data={"device_code":"device-secret","user_code":"ABCD-1234","verification_uri":"https://github.com/login/device","expires_in":900,"interval":5}
        with patch.object(GitHubAppAuth,"_post_form",return_value=data):
            result=self.auth.start_device_flow("Iv1.example")
        self.assertEqual(result["user_code"],"ABCD-1234")
        self.assertEqual(json.loads(self.auth.pending_path.read_text())["device_code"],"device-secret")
    def test_poll_pending_respects_interval(self):
        data={"device_code":"device","user_code":"ABCD","verification_uri":"https://github.com/login/device","expires_in":900,"interval":5}
        with patch.object(GitHubAppAuth,"_post_form",return_value=data),patch("node_core.github_app_auth.time.time",return_value=100):
            self.auth.start_device_flow("client")
        with patch("node_core.github_app_auth.time.time",return_value=102),patch.object(GitHubAppAuth,"_post_form",side_effect=AssertionError("too early")):
            result=self.auth.poll_device_flow()
        self.assertEqual(result["wait_seconds"],3)
    def test_poll_authorized_saves_operator_and_removes_pending(self):
        data={"device_code":"device","user_code":"ABCD","verification_uri":"https://github.com/login/device","expires_in":900,"interval":1}
        with patch.object(GitHubAppAuth,"_post_form",return_value=data),patch("node_core.github_app_auth.time.time",return_value=100):
            self.auth.start_device_flow("client")
        with patch("node_core.github_app_auth.time.time",return_value=102),patch.object(GitHubAppAuth,"_post_form",return_value={"access_token":"user-token","refresh_token":"refresh-token","expires_in":28800,"refresh_token_expires_in":15552000}),patch.object(GitHubAppAuth,"_get_json",return_value={"login":"octocat"}):
            result=self.auth.poll_device_flow("octocat")
        self.assertEqual(result["state"],"authorized")
        self.assertFalse(self.auth.pending_path.exists())
        saved=json.loads(self.auth.operator_path.read_text())
        self.assertEqual(saved["access_token"],"user-token")
        self.assertEqual(self.auth.operator_path.stat().st_mode & 0o777,0o600)
    def test_poll_rejects_wrong_account(self):
        data={"device_code":"device","user_code":"ABCD","verification_uri":"https://github.com/login/device","expires_in":900,"interval":1}
        with patch.object(GitHubAppAuth,"_post_form",return_value=data),patch("node_core.github_app_auth.time.time",return_value=100):
            self.auth.start_device_flow("client")
        with patch("node_core.github_app_auth.time.time",return_value=102),patch.object(GitHubAppAuth,"_post_form",return_value={"access_token":"token"}),patch.object(GitHubAppAuth,"_get_json",return_value={"login":"other"}):
            with self.assertRaisesRegex(GitHubAppError,"does not match"): self.auth.poll_device_flow("octocat")
        self.assertFalse(self.auth.operator_path.exists())
    def test_expired_device_code_is_removed(self):
        data={"device_code":"device","user_code":"ABCD","verification_uri":"https://github.com/login/device","expires_in":10,"interval":1}
        with patch.object(GitHubAppAuth,"_post_form",return_value=data),patch("node_core.github_app_auth.time.time",return_value=100):
            self.auth.start_device_flow("client")
        with patch("node_core.github_app_auth.time.time",return_value=111):
            result=self.auth.poll_device_flow()
        self.assertEqual(result["state"],"expired")
        self.assertFalse(self.auth.pending_path.exists())
    def test_installation_token_is_limited_to_repository_and_contents_write(self):
        key_path=Path(self.temp.name)/"app.pem"
        key_path.write_text("test-key",encoding="utf-8")
        with patch.object(GitHubAppAuth,"_create_app_jwt",return_value="app-jwt"),patch.object(GitHubAppAuth,"_post_json",return_value={"token":"installation-token"}) as request:
            token=self.auth.installation_token("1234","client","5678",key_path)
        self.assertEqual(token,"installation-token")
        self.assertEqual(request.call_args.args[2],{"repositories":["client"],"permissions":{"contents":"write"}})
    def test_app_jwt_contains_expected_issuer_and_short_expiration(self):
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        path=Path(self.temp.name)/"app.pem"
        path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        token=self.auth._create_app_jwt("12345",path)
        header,payload,signature=token.split(".")
        claims=json.loads(base64.urlsafe_b64decode(payload+"="*(-len(payload)%4)))
        self.assertEqual(claims["iss"],"12345")
        self.assertLessEqual(claims["exp"]-claims["iat"],600)
        self.assertEqual(json.loads(base64.urlsafe_b64decode(header+"="*(-len(header)%4)))["alg"],"RS256")
        self.assertTrue(signature)

if __name__=="__main__": unittest.main()
