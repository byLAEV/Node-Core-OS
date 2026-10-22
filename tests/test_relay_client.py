import base64
import json
import unittest

from scripts.node_core_relay_client import GitHubRelayClient, RelayClientError


class RelayClientTests(unittest.TestCase):
    def setUp(self):
        self.client = GitHubRelayClient("byLAEV/Node-Core-OS", "test-token")

    def test_rejects_request_outside_expected_inbox_path(self):
        with self.assertRaisesRegex(RelayClientError, "outside"):
            self.client.read_request({
                "name": "gha-1-1.json",
                "path": ".node-core-relay/receipts/gha-1-1.json",
                "download_url": "https://example.invalid/secret",
            })

    def test_rejects_invalid_filename_before_network_access(self):
        with self.assertRaisesRegex(RelayClientError, "filename"):
            self.client.read_request({
                "name": "../secrets.json",
                "path": ".node-core-relay/requests/../secrets.json",
                "download_url": "https://example.invalid/secret",
            })

    def test_reads_request_only_through_expected_github_api_path(self):
        payload = {"schema": "node-core-os/relay-delivery/v1", "run_id": "gha-1-1"}
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        calls = []

        def fake_request(method, path, body=None):
            calls.append((method, path, body))
            return 200, {"encoding": "base64", "content": encoded}

        self.client.request = fake_request
        result = self.client.read_request({
            "name": "gha-1-1.json",
            "path": ".node-core-relay/requests/gha-1-1.json",
            "download_url": "https://example.invalid/must-not-be-fetched",
        })
        self.assertEqual(result, payload)
        self.assertEqual(calls, [(
            "GET",
            "contents/.node-core-relay/requests/gha-1-1.json?ref=node-core-relay",
            None,
        )])


if __name__ == "__main__":
    unittest.main()
