#!/usr/bin/env python3
"""Read a synthetic CID from a remote Kubo peer and sign a delivery receipt.

This utility is intended for an explicitly initiated, short-lived integration
test. It never exports or prints the node's private key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCHEMA = "node-core-os/termux-remote-read-ack/v1"
MAX_CONTENT_BYTES = 1024 * 1024


def canonical_json(value: dict[str, str]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Connect to a remote Kubo peer, read a CID, and submit a signed ACK."
    )
    parser.add_argument("--peer-address", required=True, help="Kubo libp2p multiaddress.")
    parser.add_argument("--cid", required=True, help="Synthetic content CID to retrieve.")
    parser.add_argument("--expected-sha256", required=True, help="Expected SHA-256 of retrieved bytes.")
    parser.add_argument("--nonce", required=True, help="One-run challenge printed by GitHub Actions.")
    parser.add_argument("--ack-url", required=True, help="Temporary HTTP callback URL printed by GitHub Actions.")
    parser.add_argument(
        "--data-dir", type=Path,
        default=Path(os.environ.get("NODE_CORE_DATA_DIR", str(Path.home() / ".node-core"))).expanduser(),
    )
    parser.add_argument(
        "--app-root", type=Path,
        default=Path(os.environ.get("NODE_CORE_APP", str(Path.home() / ".node-core" / "app"))).expanduser(),
    )
    parser.add_argument(
        "--ipfs-executable",
        default=os.environ.get("IPFS_BIN") or (
            str(Path(os.environ["PREFIX"]) / "bin" / "ipfs")
            if os.environ.get("PREFIX") and (Path(os.environ["PREFIX"]) / "bin" / "ipfs").is_file()
            else "ipfs"
        ),
    )
    parser.add_argument(
        "--ipfs-path", type=Path,
        default=Path(os.environ.get("IPFS_PATH", str(Path.home() / ".node-core" / "ipfs"))).expanduser(),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if os.getuid() == 0:
        raise SystemExit("ERROR: this test must run as a normal user, never root.")
    if re.fullmatch(r"[0-9a-f]{64}", args.expected_sha256) is None:
        raise SystemExit("ERROR: --expected-sha256 must be 64 lowercase hexadecimal characters.")
    if not args.nonce or len(args.nonce) > 200:
        raise SystemExit("ERROR: invalid test nonce.")
    if not args.peer_address.startswith("/dns4/bore.pub/tcp/"):
        raise SystemExit("ERROR: peer address must be the temporary bore.pub multiaddress.")
    if not args.ack_url.startswith("http://bore.pub:"):
        raise SystemExit("ERROR: ACK URL must use the temporary bore.pub HTTP callback.")
    if not args.app_root.is_dir():
        raise SystemExit(f"ERROR: Node Core OS application directory not found: {args.app_root}")

    sys.path.insert(0, str(args.app_root))
    from node_core.identity.node_identity import NodeIdentityStore

    environment = os.environ.copy()
    environment["IPFS_PATH"] = str(args.ipfs_path)

    connect = subprocess.run(
        [args.ipfs_executable, "swarm", "connect", args.peer_address],
        env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=45, check=False,
    )
    if connect.returncode != 0:
        raise SystemExit(
            "FAIL: Kubo could not connect to the test peer. "
            f"stdout={connect.stdout.strip()!r}; stderr={connect.stderr.strip()!r}"
        )
    print("KUBO_CONNECT_PASS", flush=True)

    read = subprocess.run(
        [args.ipfs_executable, "cat", args.cid],
        env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=120, check=False,
    )
    if read.returncode != 0:
        detail = read.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(f"FAIL: Kubo could not retrieve CID {args.cid}: {detail}")
    if len(read.stdout) > MAX_CONTENT_BYTES:
        raise SystemExit("FAIL: retrieved content exceeds the 1 MiB integration-test limit.")

    actual_sha256 = hashlib.sha256(read.stdout).hexdigest()
    if actual_sha256 != args.expected_sha256:
        raise SystemExit(
            f"FAIL: content hash mismatch; expected={args.expected_sha256}, actual={actual_sha256}"
        )
    print(f"KUBO_REMOTE_READ_PASS cid={args.cid} sha256={actual_sha256}", flush=True)

    store = NodeIdentityStore(args.data_dir)
    identity = store.load()  # Deliberately do not create or rotate an identity.
    signed_fields = {
        "schema": SCHEMA,
        "run_nonce": args.nonce,
        "node_id": identity["node_id"],
        "cid": args.cid,
        "sha256": actual_sha256,
    }
    signature = store.sign(canonical_json(signed_fields))
    receipt = {
        **signed_fields,
        "public_key": identity["public_key"],
        "signature": signature.hex(),
    }
    request = Request(
        args.ack_url,
        data=json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Node-Core-OS-Termux-Remote-Read-Test/1"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            response_body = response.read(4096).decode("utf-8", errors="replace")
            if response.status != 200:
                raise SystemExit(f"FAIL: ACK endpoint returned HTTP {response.status}: {response_body}")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise SystemExit(f"FAIL: could not submit signed ACK: {exc}") from exc

    print(f"SIGNED_ACK_ACCEPTED node_id={identity['node_id']} cid={args.cid}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
