#!/usr/bin/env python3
"""Poll the GitHub-backed Node Core OS relay from Termux using outbound HTTPS only."""
from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from node_core.config import NodeConfig
from node_core.identity.node_identity import NodeIdentityStore
from node_core.relay_delivery import persist_and_sign_receipt, verify_request

API = "https://api.github.com"
RELAY_BRANCH = "node-core-relay"
MAX_RESPONSE_BYTES = 2_000_000


class RelayClientError(RuntimeError):
    pass


class GitHubRelayClient:
    def __init__(self, repository: str, token: str, timeout: int = 20) -> None:
        if not repository or "/" not in repository:
            raise ValueError("NODE_CORE_RELAY_REPO must use owner/repository format.")
        if not token:
            raise ValueError("NODE_CORE_RELAY_GITHUB_TOKEN is required to publish the receiver receipt.")
        self.repository = repository
        self.token = token
        self.timeout = timeout

    def request(self, method: str, path: str, body: dict | None = None):
        url = f"{API}/repos/{self.repository}/{path.lstrip('/')}"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Node-Core-OS-Relay-Client",
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, separators=(",", ":")).encode("utf-8")
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise RelayClientError("GitHub API response exceeded the size limit.")
                return response.status, json.loads(raw.decode("utf-8")) if raw else None
        except HTTPError as exc:
            raw = exc.read(4096).decode("utf-8", errors="replace")
            if exc.code == 404:
                return 404, None
            raise RelayClientError(f"GitHub API returned HTTP {exc.code}: {raw}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RelayClientError(f"Relay HTTPS request failed: {exc}") from exc

    def list_requests(self) -> list[dict]:
        path = f"contents/.node-core-relay/requests?ref={RELAY_BRANCH}"
        status, value = self.request("GET", path)
        if status == 404:
            return []
        if not isinstance(value, list):
            raise RelayClientError("Relay requests directory did not return a file list.")
        return [item for item in value if isinstance(item, dict)
                and item.get("type") == "file" and item.get("name", "").endswith(".json")]

    def read_request(self, item: dict) -> dict:
        download_url = item.get("download_url")
        if not isinstance(download_url, str) or not download_url.startswith("https://"):
            raise RelayClientError("Relay request has no valid HTTPS download URL.")
        req = Request(download_url, headers={"User-Agent": "Node-Core-OS-Relay-Client"})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise RelayClientError("Relay manifest exceeds the size limit.")
            value = json.loads(raw.decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, UnicodeError) as exc:
            raise RelayClientError(f"Unable to download relay request: {exc}") from exc
        if not isinstance(value, dict):
            raise RelayClientError("Relay request is not a JSON object.")
        return value

    def has_receipt(self, run_id: str) -> bool:
        path = f"contents/.node-core-relay/receipts/{quote(run_id, safe='')}.json?ref={RELAY_BRANCH}"
        status, _ = self.request("GET", path)
        return status == 200

    def publish_receipt(self, run_id: str, receipt: dict) -> None:
        path = f"contents/.node-core-relay/receipts/{quote(run_id, safe='')}.json"
        content = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        body = {
            "message": f"relay: receipt for {run_id}",
            "content": base64.b64encode(content).decode("ascii"),
            "branch": RELAY_BRANCH,
        }
        status, _ = self.request("PUT", path, body)
        if status not in (200, 201):
            raise RelayClientError(f"Unexpected GitHub receipt-write status: {status}")


def main() -> int:
    key_hex = os.environ.get("NODE_CORE_RELAY_HMAC_KEY", "")
    token = os.environ.get("NODE_CORE_RELAY_GITHUB_TOKEN", "")
    repository = os.environ.get("NODE_CORE_RELAY_REPO", "byLAEV/Node-Core-OS")
    try:
        # Validate secret format before connecting to GitHub.
        from node_core.relay_delivery import decode_key
        decode_key(key_hex)
        client = GitHubRelayClient(repository, token)
        config = NodeConfig.load()
        identity = NodeIdentityStore(config.data_dir)
        identity.initialize()
    except (ValueError, RuntimeError) as exc:
        print(f"Relay configuration error: {exc}", file=sys.stderr)
        return 2

    print(f"Node Core OS relay client started; repo={repository}; branch={RELAY_BRANCH}")
    print("Outbound HTTPS polling only. Press Ctrl+C to stop.")
    while True:
        try:
            for item in client.list_requests():
                try:
                    envelope = client.read_request(item)
                    run_id = envelope.get("run_id", "")
                    if not isinstance(run_id, str) or not run_id:
                        print(f"Skipping malformed request file: {item.get('name')}", file=sys.stderr)
                        continue
                    if client.has_receipt(run_id):
                        continue
                    verified = verify_request(envelope, key_hex)
                    receipt = persist_and_sign_receipt(config.data_dir, verified, identity)
                    client.publish_receipt(run_id, receipt)
                    print(
                        f"RECEIPT PUBLISHED run_id={run_id} "
                        f"sha256={verified['payload_sha256']} path={receipt['persisted_path']}"
                    )
                except (ValueError, RuntimeError, RelayClientError, OSError) as exc:
                    print(f"Request not acknowledged ({item.get('name')}): {exc}", file=sys.stderr)
        except (RelayClientError, OSError) as exc:
            print(f"Relay poll failed; retrying: {exc}", file=sys.stderr)
        time.sleep(max(5, int(os.environ.get("NODE_CORE_RELAY_POLL_SECONDS", "15"))))


if __name__ == "__main__":
    raise SystemExit(main())
