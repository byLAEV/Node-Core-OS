import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from node_core.github_binding import GitHubBindingError, GitHubNodeBinding


class FakeIdentity:
    def __init__(self):
        self.value = {"node_id": "sha256:" + "a" * 64}
    def initialize(self):
        return self.value
    def load(self):
        return self.value


class GitHubNodeBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.binding = GitHubNodeBinding(Path(self.temp.name), FakeIdentity())

    def test_configures_account_repository_page_and_node(self):
        result = self.binding.configure("OctoCat", "octocat/node-core-client")
        self.assertEqual(result["github_account"], "octocat")
        self.assertEqual(result["repository"], "octocat/node-core-client")
        self.assertEqual(result["github_pages_url"], "https://octocat.github.io/node-core-client/")
        self.assertEqual(result["node_id"], "sha256:" + "a" * 64)
        self.assertEqual(self.binding.status()["binding_status"], "configured")

    def test_rejects_repository_from_another_account(self):
        with self.assertRaises(GitHubBindingError):
            self.binding.configure("octocat", "other/client")

    def test_rejects_wrong_pages_url(self):
        with self.assertRaises(GitHubBindingError):
            self.binding.configure("octocat", "octocat/client", "https://example.invalid/")

    def test_rejects_invalid_app_installation_id(self):
        with self.assertRaises(GitHubBindingError):
            self.binding.configure("octocat", "octocat/client", github_app_installation_id="abc")

    def test_rejects_http_node_api_url_for_https_github_pages(self):
        with self.assertRaisesRegex(GitHubBindingError, "HTTPS"):
            self.binding.configure(
                "octocat", "octocat/client",
                node_api_url="http://node.example.test",
            )

    def test_adds_plain_json_record_to_local_outbox(self):
        self.binding.configure("octocat", "octocat/client")
        record = self.binding.add_record({"display_name": "Example Visitor", "message": "hello"})
        path = self.binding.outbox / (record["record_id"] + ".json")
        self.assertTrue(path.is_file())
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["fields"]["display_name"], "Example Visitor")
        self.assertEqual(saved["sync_status"], "pending")
        self.assertEqual(self.binding.status()["pending_records"], 1)

    def test_exports_static_client_with_node_binding_config(self):
        self.binding.configure(
            "octocat", "octocat/client",
            node_api_url="https://node.example.test",
        )
        target = Path(self.temp.name) / "exported-client"
        exported = self.binding.export_client_package(target)
        config = json.loads((exported / "node-core-client.json").read_text(encoding="utf-8"))
        self.assertTrue((exported / "index.html").is_file())
        self.assertTrue((exported / "assets" / "app.js").is_file())
        self.assertEqual(config["repository"], "octocat/client")
        self.assertEqual(config["node_api_url"], "https://node.example.test")
        self.assertEqual(config["node_id"], "sha256:" + "a" * 64)

    def test_export_requires_node_api_url(self):
        self.binding.configure("octocat", "octocat/client")
        with self.assertRaisesRegex(GitHubBindingError, "Node API URL"):
            self.binding.export_client_package(Path(self.temp.name) / "client")

    def test_sync_writes_record_to_owner_repository(self):
        self.binding.configure("octocat", "octocat/client")
        record = self.binding.add_record({"display_name": "Test"})
        calls = []
        def api(method, path, token, payload=None):
            calls.append((method, path, payload))
            if method == "GET":
                return {"owner": {"login": "octocat"}, "default_branch": "main"}
            return {"content": {"path": path}}
        with patch.object(self.binding, "_github_token", return_value="test-token"), patch.object(self.binding, "_api", side_effect=api):
            result = self.binding.sync()
        self.assertEqual(result["synced"], 1)
        self.assertEqual(calls[0][1], "/repos/octocat/client")
        self.assertIn("records/", calls[1][1])
        self.assertTrue(calls[1][2]["content"])
        self.assertFalse((self.binding.outbox / (record["record_id"] + ".json")).exists())
        archived = self.binding.synced_records()
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0]["record_id"], record["record_id"])
        self.assertEqual(archived[0]["sync_status"], "synced")


if __name__ == "__main__":
    unittest.main()
