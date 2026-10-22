"""Termux-side outbound polling client for the authenticated manifest relay."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from node_core.identity.node_identity import NodeIdentityStore
from node_core.relay_delivery import canonical_json_bytes, persist_and_sign_receipt, verify_request


def _request(method: str, url: str, body: bytes, key_hex: str, timeout: int = 20) -> dict:
    from node_core.relay_delivery import decode_key
    parsed = urlparse(url)
    if parsed.scheme != "https" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Relay URL must use HTTPS unless connecting to loopback.")
    key = decode_key(key_hex)
    path = parsed.path or "/"
    message = method.encode() + b"\n" + path.encode() + b"\n" + body
    signature = hmac.new(key, message, hashlib.sha256).hexdigest()
    request = Request(url, data=body if method in {"POST", "PUT"} else None, method=method)
    request.add_header("X-Node-Core-Auth", signature)
    request.add_header("Content-Type", "application/json")
    request.add_header("Cache-Control", "no-store")
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(1024 * 1024 + 1)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Relay request failed: {exc}") from exc
    if len(raw) > 1024 * 1024:
        raise RuntimeError("Relay response exceeded 1 MiB.")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Relay returned invalid JSON.") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Relay response must be a JSON object.")
    return value


def process_once(base_url: str, key_hex: str, data_dir: Path) -> bool:
    envelope = _request("GET", base_url.rstrip("/") + "/v1/next", b"", key_hex)
    if envelope.get("status") == "empty":
        return False
    verified = verify_request(envelope, key_hex)
    identity = NodeIdentityStore(data_dir)
    receipt = persist_and_sign_receipt(data_dir, verified, identity)
    body = canonical_json_bytes(receipt)
    _request("POST", base_url.rstrip("/") + "/v1/receipt", body, key_hex)
    print(f"Persisted manifest run_id={receipt['run_id']} sha256={receipt['payload_sha256']}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Process at most one manifest and exit.")
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".node-core")
    args = parser.parse_args()
    base_url = os.environ.get("NODE_CORE_RELAY_URL", "").rstrip("/")
    key_hex = os.environ.get("NODE_CORE_RELAY_HMAC_KEY", "")
    if not base_url or not key_hex:
        parser.error("Set NODE_CORE_RELAY_URL and NODE_CORE_RELAY_HMAC_KEY.")
    if args.poll_seconds < 1 or args.poll_seconds > 300:
        parser.error("--poll-seconds must be between 1 and 300.")
    identity = NodeIdentityStore(args.data_dir)
    metadata = identity.initialize()
    print(f"Relay receiver ready: node_id={metadata['node_id']}; data_dir={args.data_dir}")
    while True:
        try:
            processed = process_once(base_url, key_hex, args.data_dir)
        except (RuntimeError, ValueError, OSError) as exc:
            print(f"Relay poll error: {exc}")
            processed = False
        if args.once:
            return 0 if processed else 2
        time.sleep(0.5 if processed else args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
