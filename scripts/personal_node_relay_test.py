#!/usr/bin/env python3
"""Publish one synthetic relay request and require a signed receipt from the personal node."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = "https://api.github.com"
BRANCH = "node-core-relay"
REPO = os.environ.get("GITHUB_REPOSITORY", "byLAEV/Node-Core-OS")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
KEY = os.environ.get("NODE_CORE_RELAY_HMAC_KEY", "")
EXPECTED_PUBLIC_KEY = os.environ.get("NODE_CORE_RELAY_NODE_PUBLIC_KEY", "").lower()
RUN_ID = f"gha-{os.environ.get('GITHUB_RUN_ID', 'local')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
TIMEOUT_SECONDS = max(30, min(1800, int(os.environ.get("RELAY_TIMEOUT_SECONDS", "300"))))
POLL_SECONDS = max(5, min(60, int(os.environ.get("RELAY_POLL_SECONDS", "10"))))


def canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def api(method: str, path: str, body: dict | None = None):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Node-Core-OS-Relay-Test",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, separators=(",", ":")).encode()
    req = Request(f"{ROOT}/repos/{REPO}/{path.lstrip('/')}", data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=20) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise RuntimeError("GitHub API response exceeded 2 MB.")
            return response.status, json.loads(raw.decode()) if raw else None
    except HTTPError as exc:
        raw = exc.read(4096).decode("utf-8", errors="replace")
        if exc.code == 404:
            return 404, None
        raise RuntimeError(f"GitHub API HTTP {exc.code}: {raw}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"GitHub API network error: {exc}") from exc


def put_json(path: str, value: dict, message: str) -> None:
    body = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    status, _ = api("PUT", f"contents/{path}", {
        "message": message,
        "content": base64.b64encode(body).decode("ascii"),
        "branch": BRANCH,
    })
    if status not in (200, 201):
        raise RuntimeError(f"Unexpected GitHub contents API status {status} writing {path}.")


def main() -> int:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is required.")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", KEY):
        raise RuntimeError("Set repository Actions secret NODE_CORE_RELAY_HMAC_KEY to 64 hex characters (32 random bytes).")
    if not re.fullmatch(r"[0-9a-f]{64}", EXPECTED_PUBLIC_KEY):
        raise RuntimeError("Set NODE_CORE_RELAY_NODE_PUBLIC_KEY to the personal node's 64-character Ed25519 public key hex.")

    from node_core.relay_delivery import SCHEMA, create_request

    payload = {
        "kind": "synthetic_delivery_test",
        "message": "GitHub Actions -> personal Node Core OS delivery proof. No personal data.",
        "source": "github-actions",
    }
    envelope = create_request(RUN_ID, payload, KEY)

    status, _ = api("GET", f"git/ref/heads/{BRANCH}")
    if status == 404:
        commit_sha = os.environ.get("GITHUB_SHA", "")
        if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
            raise RuntimeError("GITHUB_SHA is not a full commit SHA; cannot initialize relay branch.")
        status, _ = api("POST", "git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": commit_sha})
        if status not in (200, 201):
            status, _ = api("GET", f"git/ref/heads/{BRANCH}")
            if status != 200:
                raise RuntimeError("Unable to initialize relay branch.")

    request_path = f".node-core-relay/requests/{RUN_ID}.json"
    put_json(request_path, envelope, f"relay: enqueue synthetic request {RUN_ID}")
    print(f"REQUEST_PUBLISHED run_id={RUN_ID} payload_sha256={envelope['payload_sha256']}")
    print(f"Waiting up to {TIMEOUT_SECONDS}s for a signed receipt from the personal node...")

    receipt_path = f".node-core-relay/receipts/{RUN_ID}.json"
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        status, item = api("GET", f"contents/{receipt_path}?ref={BRANCH}")
        if status == 200:
            try:
                receipt_bytes = base64.b64decode(item["content"], validate=False)
                receipt = json.loads(receipt_bytes.decode("utf-8"))
            except (KeyError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"Receiver receipt file is malformed: {exc}") from exc
            signature_hex = receipt.get("signature_ed25519", "")
            unsigned = {k: v for k, v in receipt.items() if k != "signature_ed25519"}
            if receipt.get("schema") != SCHEMA or receipt.get("status") != "persisted":
                raise RuntimeError("Receipt schema or persisted status is invalid.")
            if receipt.get("run_id") != RUN_ID:
                raise RuntimeError("Receipt run_id does not match this workflow execution.")
            if receipt.get("payload_sha256") != envelope["payload_sha256"]:
                raise RuntimeError("Receiver acknowledged a different payload SHA-256.")
            if receipt.get("public_key", "").lower() != EXPECTED_PUBLIC_KEY:
                raise RuntimeError("Receipt public key does not match NODE_CORE_RELAY_NODE_PUBLIC_KEY.")
            public_bytes = bytes.fromhex(EXPECTED_PUBLIC_KEY)
            expected_node_id = "sha256:" + hashlib.sha256(public_bytes).hexdigest()
            if receipt.get("node_id") != expected_node_id:
                raise RuntimeError("Receipt node_id does not match the pinned Ed25519 public key.")
            persisted_path = receipt.get("persisted_path", "")
            normalized_path = persisted_path.replace("\\\\", "/") if isinstance(persisted_path, str) else ""
            expected_suffix = f"/storage/relay/inbox/{RUN_ID}.json"
            if not normalized_path.endswith(expected_suffix):
                raise RuntimeError("Receipt does not prove persistence under storage/relay/inbox for this run.")
            if not isinstance(receipt.get("received_at_utc"), str) or not receipt["received_at_utc"]:
                raise RuntimeError("Receipt is missing its receiver timestamp.")
            if not re.fullmatch(r"[0-9a-fA-F]{128}", signature_hex):
                raise RuntimeError("Receiver Ed25519 signature is missing or malformed.")
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            from cryptography.exceptions import InvalidSignature
            try:
                Ed25519PublicKey.from_public_bytes(public_bytes).verify(bytes.fromhex(signature_hex), canonical(unsigned))
            except (InvalidSignature, ValueError) as exc:
                raise RuntimeError("Receiver Ed25519 signature verification failed.") from exc

            summary = os.environ.get("GITHUB_STEP_SUMMARY")
            if summary:
                with open(summary, "a", encoding="utf-8") as handle:
                    handle.write("## Personal Node Core OS relay delivery\n\n")
                    handle.write("- Result: **RECEIVER CONFIRMED**\n")
                    handle.write(f"- Run ID: **{RUN_ID}**\n")
                    handle.write(f"- Payload SHA-256: **{envelope['payload_sha256']}**\n")
                    handle.write(f"- Receiver node ID: **{receipt['node_id']}**\n")
                    handle.write(f"- Receiver persisted path: **{receipt['persisted_path']}**\n")
                    handle.write(f"- Receiver timestamp (UTC): **{receipt['received_at_utc']}**\n")
                    handle.write("- Receipt: Ed25519 signature verified against the pinned public key.\n")
            print(f"RECEIVER_CONFIRMED run_id={RUN_ID} payload_sha256={envelope['payload_sha256']}")
            print(f"RECEIVER_NODE_ID={receipt['node_id']}")
            print(f"PERSISTED_PATH={receipt['persisted_path']}")
            print(f"RECEIVED_AT_UTC={receipt['received_at_utc']}")
            return 0
        time.sleep(POLL_SECONDS)

    raise RuntimeError(
        f"No valid receiver receipt arrived within {TIMEOUT_SECONDS}s. "
        "The workflow will fail; publication alone is not considered delivery."
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PERSONAL NODE RELAY TEST FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
