"""GitHub Actions-side sender and Ed25519 receipt verifier."""
import argparse, hashlib, hmac, json, os, time
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from node_core.relay_delivery import canonical_json_bytes, create_request, decode_key

def relay_request(method, url, body, key_hex):
    parsed = urlparse(url)
    if parsed.scheme != "https" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Relay URL must use HTTPS except loopback.")
    key = decode_key(key_hex)
    path = parsed.path or "/"
    sig = hmac.new(key, method.encode()+b"\n"+path.encode()+b"\n"+body, hashlib.sha256).hexdigest()
    req = Request(url, data=body if method == "POST" else None, method=method)
    req.add_header("X-Node-Core-Auth", sig)
    req.add_header("Content-Type", "application/json")
    req.add_header("Cache-Control", "no-store")
    with urlopen(req, timeout=20) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise RuntimeError("Relay response exceeded 1 MiB.")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError("Relay response must be an object.")
    return value

def verify_receipt(receipt, run_id, digest, expected_public_key):
    if receipt.get("status") != "persisted" or receipt.get("run_id") != run_id:
        raise ValueError("Receipt status/run_id mismatch.")
    if receipt.get("payload_sha256") != digest:
        raise ValueError("Receipt SHA-256 does not match sent payload.")
    public_hex = receipt.get("public_key", "")
    if not hmac.compare_digest(public_hex, expected_public_key.lower()):
        raise ValueError("Receipt public key does not match configured receiver.")
    unsigned = {k:v for k,v in receipt.items() if k != "signature_ed25519"}
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex)).verify(
            bytes.fromhex(receipt["signature_ed25519"]), canonical_json_bytes(unsigned))
    except Exception as exc:
        raise ValueError("Receiver Ed25519 signature is invalid.") from exc
    node_id = "sha256:" + hashlib.sha256(bytes.fromhex(public_hex)).hexdigest()
    if receipt.get("node_id") != node_id:
        raise ValueError("Receipt node_id does not derive from public key.")
    path = receipt.get("persisted_path", "").replace("\\", "/")
    if "/storage/relay/inbox/" not in path:
        raise ValueError("Receipt does not identify the persistent relay inbox.")
    
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id",required=True); p.add_argument("--repository",required=True)
    p.add_argument("--commit",required=True); p.add_argument("--wait-seconds",type=int,default=300)
    a=p.parse_args()
    base=os.environ.get("NODE_CORE_RELAY_URL","").rstrip("/")
    key=os.environ.get("NODE_CORE_RELAY_HMAC_KEY","")
    expected=os.environ.get("NODE_CORE_RELAY_EXPECTED_NODE_PUBLIC_KEY","").lower()
    if not base or not key or len(expected)!=64:
        p.error("Set NODE_CORE_RELAY_URL, NODE_CORE_RELAY_HMAC_KEY, and NODE_CORE_RELAY_EXPECTED_NODE_PUBLIC_KEY (64 hex chars).")
    if not 1 <= a.wait_seconds <= 1800: p.error("--wait-seconds must be 1..1800")
    payload={"manifest_type":"node-core-os-relay-smoke-test","schema":"node-core-os/test-manifest/v1",
      "repository":a.repository,"commit":a.commit,"run_id":a.run_id,
      "created_at_utc":datetime.now(timezone.utc).isoformat(),"synthetic":True,
      "purpose":"Verify authenticated GitHub Actions delivery to local persistent Node Core OS storage."}
    envelope=create_request(a.run_id,payload,key)
    queued=relay_request("POST",base+"/v1/manifest",canonical_json_bytes(envelope),key)
    if queued.get("status")!="queued" or queued.get("run_id")!=a.run_id:
        raise RuntimeError("Relay did not confirm manifest queueing.")
    digest=envelope["payload_sha256"]
    print(f"Queued synthetic manifest run_id={a.run_id} sha256={digest}")
    deadline=time.monotonic()+a.wait_seconds
    url=base+"/v1/receipt?"+urlencode({"run_id":a.run_id})
    while time.monotonic()<deadline:
        receipt=relay_request("GET",url,b"",key)
        if receipt.get("status")=="persisted":
            verify_receipt(receipt,a.run_id,digest,expected)
            print(f"RECEIVED_AND_VERIFIED run_id={a.run_id} node_id={receipt['node_id']} sha256={digest}")
            return 0
        time.sleep(5)
    raise TimeoutError(f"No valid receiver receipt within {a.wait_seconds} seconds.")
if __name__=="__main__": raise SystemExit(main())
