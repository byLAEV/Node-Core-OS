"""Independent certificate bundle verifier built on Python stdlib and OpenSSL.

This CLI verifies bundle inventory hashes and X.509 path/identity using a
trust bundle supplied independently by the operator. It does not implement
NODE identity binding signatures, UTXO authorization, or certificate issuance.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from . import __version__


FORMAT = "NODE-PKI-GUARD-X509-BUNDLE"
VERSION = "1.0"
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
MAX_FILES = 128
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class VerificationError(Exception):
    """Raised when a manifest, artifact, or OpenSSL check is rejected."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    try:
        if path.stat().st_size > MAX_MANIFEST_BYTES:
            raise VerificationError("manifest exceeds the 1 MiB size limit")
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except VerificationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot read manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise VerificationError("manifest root must be a JSON object")
    return value


def _safe_relative_path(value: Any, *, field: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise VerificationError(f"{field} must be a relative POSIX path")
    if "\\" in value or "\x00" in value:
        raise VerificationError(f"{field} contains a forbidden path character")
    path = PurePosixPath(value)
    if path.is_absolute() or value.startswith("/") or any(part in {"", ".", ".."} for part in value.split("/")):
        raise VerificationError(f"{field} must not be absolute or traverse parent directories")
    if path.as_posix() != value:
        raise VerificationError(f"{field} must use a normalized POSIX path")
    if not all(re.fullmatch(r"[A-Za-z0-9._-]+", part) for part in path.parts):
        raise VerificationError(f"{field} contains an unsupported path character")
    return path


def _bundle_file(root: Path, relative_path: PurePosixPath, *, field: str) -> Path:
    root_resolved = root.resolve(strict=True)
    candidate = root_resolved.joinpath(*relative_path.parts)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root_resolved)
    except (OSError, ValueError) as exc:
        raise VerificationError(f"{field} is missing or escapes the bundle directory") from exc
    if not resolved.is_file():
        raise VerificationError(f"{field} is not a regular file")
    try:
        size = resolved.stat().st_size
    except OSError as exc:
        raise VerificationError(f"cannot stat {field}") from exc
    if size <= 0 or size > MAX_ARTIFACT_BYTES:
        raise VerificationError(f"{field} must be between 1 byte and 16 MiB")
    return resolved


def _validate_timestamp(value: Any, *, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise VerificationError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise VerificationError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise VerificationError(f"{field} must include a timezone")


def _validate_manifest_structure(manifest: dict[str, Any]) -> tuple[PurePosixPath, str, str]:
    allowed_top = {
        "format", "version", "bundle_id", "created_at", "certificate",
        "files", "node_binding", "trust_statement",
    }
    if set(manifest) - allowed_top:
        raise VerificationError("manifest contains unknown top-level fields")
    if manifest.get("format") != FORMAT or manifest.get("version") != VERSION:
        raise VerificationError("unsupported bundle format or version")
    bundle_id = manifest.get("bundle_id")
    if not isinstance(bundle_id, str) or not bundle_id or len(bundle_id) > 128:
        raise VerificationError("bundle_id must be a non-empty string of at most 128 characters")
    _validate_timestamp(manifest.get("created_at"), field="created_at")

    certificate = manifest.get("certificate")
    if not isinstance(certificate, dict):
        raise VerificationError("certificate must be an object")
    allowed_certificate = {
        "path", "encoding", "sha256_fingerprint", "spki_sha256", "subject",
        "issuer", "serial_number_hex", "not_before", "not_after",
    }
    if set(certificate) - allowed_certificate:
        raise VerificationError("certificate contains unknown fields")
    for required in ("path", "encoding", "sha256_fingerprint", "spki_sha256"):
        if required not in certificate:
            raise VerificationError(f"certificate.{required} is required")
    cert_path = _safe_relative_path(certificate["path"], field="certificate.path")
    if certificate["encoding"] not in {"PEM", "DER"}:
        raise VerificationError("certificate.encoding must be PEM or DER")
    for field in ("sha256_fingerprint", "spki_sha256"):
        value = certificate[field]
        if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
            raise VerificationError(f"certificate.{field} must be lowercase SHA-256 hex")
    if "not_before" in certificate:
        _validate_timestamp(certificate["not_before"], field="certificate.not_before")
    if "not_after" in certificate:
        _validate_timestamp(certificate["not_after"], field="certificate.not_after")
    if "serial_number_hex" in certificate:
        serial = certificate["serial_number_hex"]
        if not isinstance(serial, str) or not re.fullmatch(r"[0-9a-fA-F]+", serial):
            raise VerificationError("certificate.serial_number_hex is invalid")

    entries = manifest.get("files")
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_FILES:
        raise VerificationError(f"files must contain between 1 and {MAX_FILES} entries")
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) - {"path", "sha256", "media_type"}:
            raise VerificationError(f"files[{index}] contains invalid fields")
        if "path" not in entry or "sha256" not in entry:
            raise VerificationError(f"files[{index}] requires path and sha256")
        item_path = _safe_relative_path(entry["path"], field=f"files[{index}].path")
        if item_path.as_posix() in seen:
            raise VerificationError("manifest contains duplicate file paths")
        seen.add(item_path.as_posix())
        digest = entry["sha256"]
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise VerificationError(f"files[{index}].sha256 must be lowercase SHA-256 hex")
        if "media_type" in entry and (
            not isinstance(entry["media_type"], str) or len(entry["media_type"]) > 128
        ):
            raise VerificationError(f"files[{index}].media_type is invalid")
    if cert_path.as_posix() not in seen:
        raise VerificationError("certificate.path must also appear in files inventory")

    binding = manifest.get("node_binding")
    if binding is not None:
        if not isinstance(binding, dict) or set(binding) != {"path", "format", "version"}:
            raise VerificationError("node_binding must contain path, format, and version only")
        binding_path = _safe_relative_path(binding["path"], field="node_binding.path")
        if binding["format"] != "NODE-PKI-BINDING" or not isinstance(binding["version"], str):
            raise VerificationError("unsupported NODE-PKI-BINDING declaration")
        if binding_path.as_posix() not in seen:
            raise VerificationError("node_binding.path must appear in files inventory")

    trust_statement = manifest.get("trust_statement", "")
    if not isinstance(trust_statement, str) or len(trust_statement) > 2048:
        raise VerificationError("trust_statement must be a string of at most 2048 characters")
    return cert_path, certificate["encoding"], certificate["sha256_fingerprint"]


def _verify_inventory(root: Path, manifest: dict[str, Any]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for entry in manifest["files"]:
        relative = _safe_relative_path(entry["path"], field="files.path")
        path = _bundle_file(root, relative, field=relative.as_posix())
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            raise VerificationError(f"SHA-256 inventory mismatch: {relative.as_posix()}")
        hashes[relative.as_posix()] = actual
    return hashes


def _run_openssl(
    binary: str,
    arguments: list[str],
    *,
    timeout: float = 15.0,
    input_data: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            [binary, *arguments],
            input=input_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
            stdin=subprocess.DEVNULL if input_data is None else None,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"},
        )
    except subprocess.TimeoutExpired as exc:
        raise VerificationError("OpenSSL command timed out") from exc
    except OSError as exc:
        raise VerificationError(f"cannot execute OpenSSL: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).decode("utf-8", errors="replace").strip()
        raise VerificationError("OpenSSL rejected the input: " + detail[-3000:])
    return result


def _openssl_details(binary: str) -> tuple[str, int]:
    result = _run_openssl(binary, ["version"])
    version = (result.stdout or result.stderr).decode("utf-8", errors="replace").strip()
    match = re.search(r"^OpenSSL\s+(\d+)\.", version)
    if not match:
        raise VerificationError("OpenSSL 1.1.1 or newer is required; unrecognized version output")
    major = int(match.group(1))
    if major < 1:
        raise VerificationError("OpenSSL 1.1.1 or newer is required")
    return version, major


def _external_file(path: Path, *, field: str) -> Path:
    try:
        resolved = path.expanduser().resolve(strict=True)
    except OSError as exc:
        raise VerificationError(f"{field} does not exist: {path}") from exc
    if not resolved.is_file() or resolved.stat().st_size <= 0 or resolved.stat().st_size > MAX_ARTIFACT_BYTES:
        raise VerificationError(f"{field} must be a regular file between 1 byte and 16 MiB")
    return resolved


def verify_bundle(
    *,
    bundle_dir: Path,
    ca_file: Path,
    hostname: str | None = None,
    ip_address: str | None = None,
    purpose: str = "sslserver",
    manifest_name: str = "manifest.json",
    intermediates: Path | None = None,
    crl_file: Path | None = None,
    require_crl: bool = False,
    auth_level: int = 2,
    verify_depth: int = 8,
    openssl_binary: str = "openssl",
) -> dict[str, Any]:
    """Validate inventory hashes, certificate fingerprints, and OpenSSL trust."""
    if bool(hostname) == bool(ip_address):
        raise VerificationError("provide exactly one of --hostname or --ip")
    if purpose not in {"sslserver", "sslclient"}:
        raise VerificationError("purpose must be sslserver or sslclient")
    if type(auth_level) is not int or not 0 <= auth_level <= 5:
        raise VerificationError("auth_level must be from 0 through 5")
    if type(verify_depth) is not int or not 0 <= verify_depth <= 32:
        raise VerificationError("verify_depth must be from 0 through 32")
    if require_crl and crl_file is None:
        raise VerificationError("--require-crl requires --crl-file")
    if hostname:
        if len(hostname) > 253 or hostname.endswith(".") or "*" in hostname:
            raise VerificationError("invalid expected hostname")
        try:
            hostname = hostname.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise VerificationError("invalid expected hostname") from exc
    if ip_address:
        try:
            ip_address = str(ipaddress.ip_address(ip_address))
        except ValueError as exc:
            raise VerificationError("--ip must be a valid IPv4 or IPv6 address") from exc

    root = bundle_dir.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise VerificationError("bundle directory is not a directory")
    manifest_relative = _safe_relative_path(manifest_name, field="manifest name")
    manifest_path = _bundle_file(root, manifest_relative, field="manifest")
    manifest = _load_json(manifest_path)
    cert_relative, encoding, declared_fingerprint = _validate_manifest_structure(manifest)
    inventory_hashes = _verify_inventory(root, manifest)
    certificate_file = _bundle_file(root, cert_relative, field="certificate")

    binary = shutil.which(openssl_binary)
    if binary is None:
        raise VerificationError(f"OpenSSL executable not found: {openssl_binary}")
    version, major = _openssl_details(binary)
    trusted_ca = _external_file(ca_file, field="CA trust bundle")
    intermediate_file = _external_file(intermediates, field="intermediate bundle") if intermediates else None
    crl_path = _external_file(crl_file, field="CRL bundle") if crl_file else None

    with tempfile.TemporaryDirectory(prefix="node-pki-guard-cli-") as temporary:
        temp_root = Path(temporary)
        certificate_pem = temp_root / "certificate.pem"
        if encoding == "PEM":
            certificate_pem.write_bytes(certificate_file.read_bytes())
            _run_openssl(binary, ["x509", "-in", str(certificate_pem), "-noout"])
        else:
            _run_openssl(binary, [
                "x509", "-inform", "DER", "-in", str(certificate_file),
                "-out", str(certificate_pem),
            ])
        der = _run_openssl(binary, [
            "x509", "-in", str(certificate_pem), "-outform", "DER",
        ]).stdout
        certificate_fingerprint = hashlib.sha256(der).hexdigest()
        if certificate_fingerprint != declared_fingerprint:
            raise VerificationError("certificate fingerprint does not match manifest")

        public_key_pem = _run_openssl(binary, [
            "x509", "-in", str(certificate_pem), "-pubkey", "-noout",
        ]).stdout
        public_key_der = _run_openssl(
            binary, ["pkey", "-pubin", "-outform", "DER"], input_data=public_key_pem
        ).stdout
        spki_fingerprint = hashlib.sha256(public_key_der).hexdigest()
        if spki_fingerprint != manifest["certificate"]["spki_sha256"]:
            raise VerificationError("certificate SPKI fingerprint does not match manifest")

        command = [
            "verify", "-verbose", "-show_chain", "-x509_strict",
            "-auth_level", str(auth_level), "-verify_depth", str(verify_depth),
            "-purpose", purpose, "-CAfile", str(trusted_ca), "-no-CApath",
        ]
        if major >= 3:
            command.append("-no-CAstore")
        if hostname:
            command.extend(["-verify_hostname", hostname])
            identity = hostname
        else:
            command.extend(["-verify_ip", ip_address or ""])
            identity = ip_address or ""
        if intermediate_file:
            command.extend(["-untrusted", str(intermediate_file)])
        if crl_path:
            command.extend(["-CRLfile", str(crl_path)])
            command.append("-crl_check_all")
        command.append(str(certificate_pem))
        verification = _run_openssl(binary, command, timeout=30.0)
        output = (verification.stdout or verification.stderr).decode("utf-8", errors="replace").strip()

    return {
        "valid": True,
        "bundle_id": manifest["bundle_id"],
        "certificate_sha256": certificate_fingerprint,
        "spki_sha256": spki_fingerprint,
        "openssl_version": version,
        "purpose": purpose,
        "identity": identity,
        "revocation_checked": crl_path is not None,
        "inventory_files_verified": len(inventory_hashes),
        "node_binding_present": "node_binding" in manifest,
        "openssl_output": output,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="node-pki-guard",
        description="Verify a NODE-PKI-GUARD X.509 bundle with system OpenSSL.",
        epilog=(
            "Trust is supplied independently through --ca-file. A bundle manifest "
            "never establishes trust by itself. NODE binding and UTXO authorization "
            "are not validated by this generic X.509 verifier."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify", help="verify bundle integrity, X.509 chain, and peer identity")
    verify.add_argument("--bundle-dir", type=Path, required=True)
    verify.add_argument("--manifest", default="manifest.json")
    verify.add_argument("--ca-file", type=Path, required=True, help="independently trusted CA bundle")
    identity = verify.add_mutually_exclusive_group(required=True)
    identity.add_argument("--hostname", help="expected DNS hostname")
    identity.add_argument("--ip", dest="ip_address", help="expected IP address")
    verify.add_argument("--purpose", choices=("sslserver", "sslclient"), default="sslserver")
    verify.add_argument("--intermediates", type=Path, help="untrusted intermediate CA bundle")
    verify.add_argument("--crl-file", type=Path, help="CRL bundle for revocation checking")
    verify.add_argument("--require-crl", action="store_true", help="fail unless a CRL is supplied and checked")
    verify.add_argument("--auth-level", type=int, choices=range(0, 6), default=2)
    verify.add_argument("--verify-depth", type=int, choices=range(0, 33), default=8)
    verify.add_argument("--openssl", default="openssl", help="OpenSSL executable or absolute path")
    verify.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            result = verify_bundle(
                bundle_dir=args.bundle_dir,
                ca_file=args.ca_file,
                hostname=args.hostname,
                ip_address=args.ip_address,
                purpose=args.purpose,
                manifest_name=args.manifest,
                intermediates=args.intermediates,
                crl_file=args.crl_file,
                require_crl=args.require_crl,
                auth_level=args.auth_level,
                verify_depth=args.verify_depth,
                openssl_binary=args.openssl,
            )
            if args.json:
                print(json.dumps(result, sort_keys=True, indent=2))
            else:
                print("NODE-PKI-GUARD bundle verification: PASS")
                print(f"Bundle: {result['bundle_id']}")
                print(f"Certificate SHA-256: {result['certificate_sha256']}")
                print(f"SPKI SHA-256: {result['spki_sha256']}")
                print(f"OpenSSL: {result['openssl_version']}")
                print(f"Purpose: {result['purpose']}")
                print(f"Identity: {result['identity']}")
                print(f"Inventory files verified: {result['inventory_files_verified']}")
                print(f"Revocation checked: {'YES' if result['revocation_checked'] else 'NO'}")
                if result["node_binding_present"]:
                    print("NODE binding: present (not validated by generic X.509 CLI)")
        return 0
    except (VerificationError, OSError) as exc:
        print(f"node-pki-guard: ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
