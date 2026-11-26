"""Shared runtime self-test for Node Core OS cryptography."""
from __future__ import annotations
import argparse, json, re, sys
from typing import Any
from cryptography import __version__ as VERSION
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

class CryptoHealthError(RuntimeError):
    """Cryptographic dependency or primitive failed validation."""

def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise CryptoHealthError(f"Unrecognized cryptography version: {value}")
    return tuple(map(int, match.groups()))

def run_self_test() -> dict[str, Any]:
    version = _version_tuple(VERSION)
    if version < (42, 0, 0):
        raise CryptoHealthError(f"cryptography {VERSION} is below required 42.0.0")
    try:
        private = Ed25519PrivateKey.generate()
        public = private.public_key()
        message = b"Node Core OS cryptographic runtime self-test v1"
        signature = private.sign(message)
        public.verify(signature, message)
        try:
            public.verify(signature, message + b" altered")
        except InvalidSignature:
            pass
        else:
            raise CryptoHealthError("Ed25519 accepted altered message data")
        pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        restored = serialization.load_pem_private_key(pem, password=None)
        if not isinstance(restored, Ed25519PrivateKey):
            raise CryptoHealthError("PKCS8 PEM round-trip returned a different key type")
        raw = restored.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        Ed25519PublicKey.from_public_bytes(raw).verify(restored.sign(message), message)
        digest = hashes.Hash(hashes.SHA256()); digest.update(b"abc")
        if digest.finalize().hex() != "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad":
            raise CryptoHealthError("SHA-256 known-answer test failed")
    except CryptoHealthError:
        raise
    except Exception as exc:
        raise CryptoHealthError(f"{type(exc).__name__}: {exc}") from exc
    return {"status":"success","cryptography_version":VERSION,"minimum_version":"42.0.0",
            "checks":["version","ed25519-generation","ed25519-sign-verify","tamper-rejection","pkcs8-pem-roundtrip","sha256-known-answer"]}

def main() -> int:
    parser=argparse.ArgumentParser(description="Node Core OS cryptographic self-test")
    parser.add_argument("--json",action="store_true"); args=parser.parse_args()
    try: result=run_self_test()
    except Exception as exc:
        result={"status":"failure","error_type":type(exc).__name__,"error":str(exc),
                "recovery":"Preserve node identity files. Verify the exact private Python interpreter; repair cryptography only in that environment, then rerun this self-test. Never regenerate an existing identity key."}
        if args.json: print(json.dumps(result,sort_keys=True))
        else:
            print("CRYPTOGRAPHIC SELF-TEST FAILED",file=sys.stderr); print(result["error"],file=sys.stderr); print(result["recovery"],file=sys.stderr)
        return 1
    print(json.dumps(result,sort_keys=True) if args.json else f"Cryptographic self-test: SUCCESS (cryptography {VERSION})")
    return 0

if __name__=="__main__": raise SystemExit(main())
