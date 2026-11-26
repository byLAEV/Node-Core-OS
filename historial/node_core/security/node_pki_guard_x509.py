"""OpenSSL-backed X.509 path and peer-identity validation for NODE-PKI-GUARD.

The caller supplies an explicit trust bundle. No system trust store is silently
added. This module validates certificate path, TLS purpose, time, hostname/IP,
and optionally CRL status. It does not perform NODE binding or UTXO checks.
"""
from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Literal

from cryptography import x509

from node_core.security.node_pki_guard import (
    NodePKIGuardError,
    certificate_fingerprints,
)


class OpenSSLVerificationError(NodePKIGuardError):
    """Raised when OpenSSL cannot validate the supplied X.509 certificate."""


@dataclass(frozen=True)
class X509ValidationPolicy:
    ca_bundle_pem: bytes
    purpose: Literal["sslserver", "sslclient"]
    expected_hostname: str | None = None
    expected_ip: str | None = None
    intermediate_bundle_pem: bytes | None = None
    crl_bundle_pem: bytes | None = None
    require_crl: bool = False
    check_all_crl: bool = True
    auth_level: int = 2
    verify_depth: int = 8
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not isinstance(self.ca_bundle_pem, bytes) or not self.ca_bundle_pem.strip():
            raise ValueError("An explicit non-empty CA bundle is required")
        if self.purpose not in {"sslserver", "sslclient"}:
            raise ValueError("purpose must be sslserver or sslclient")
        if bool(self.expected_hostname) == bool(self.expected_ip):
            raise ValueError("Provide exactly one expected_hostname or expected_ip")
        if self.expected_hostname is not None:
            host = self.expected_hostname.rstrip(".")
            if not host or len(host) > 253 or host.startswith("-"):
                raise ValueError("Invalid expected hostname")
            try:
                ascii_host = host.encode("idna").decode("ascii")
            except UnicodeError as exc:
                raise ValueError("Invalid internationalized hostname") from exc
            if any(not label or len(label) > 63 for label in ascii_host.split(".")):
                raise ValueError("Invalid expected hostname labels")
        if self.expected_ip is not None:
            try:
                ipaddress.ip_address(self.expected_ip)
            except ValueError as exc:
                raise ValueError("expected_ip must be an IPv4 or IPv6 address") from exc
        if self.intermediate_bundle_pem is not None and not self.intermediate_bundle_pem.strip():
            raise ValueError("intermediate_bundle_pem cannot be empty")
        if self.crl_bundle_pem is not None and not self.crl_bundle_pem.strip():
            raise ValueError("crl_bundle_pem cannot be empty")
        if self.require_crl and self.crl_bundle_pem is None:
            raise ValueError("Revocation is required but no CRL bundle was supplied")
        if type(self.auth_level) is not int or self.auth_level not in range(0, 6):
            raise ValueError("auth_level must be an integer from 0 through 5")
        if type(self.verify_depth) is not int or self.verify_depth < 0 or self.verify_depth > 32:
            raise ValueError("verify_depth must be an integer from 0 through 32")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 120:
            raise ValueError("timeout_seconds must be greater than 0 and at most 120")


@dataclass(frozen=True)
class X509ValidationResult:
    validated: bool
    certificate_fingerprint_sha256: str
    spki_sha256: str
    openssl_version: str
    purpose: str
    identity_checked: str
    revocation_checked: bool
    verification_output: str


def _write_private_file(directory: str, filename: str, content: bytes) -> str:
    path = Path(directory) / filename
    path.write_bytes(content)
    try:
        path.chmod(0o600)
    except OSError as exc:
        raise OpenSSLVerificationError("Could not set restrictive temporary file permissions") from exc
    return str(path)


def _openssl_version(binary: str, timeout_seconds: float) -> tuple[str, int]:
    try:
        result = subprocess.run(
            [binary, "version"], check=False, capture_output=True, text=True,
            timeout=timeout_seconds, stdin=subprocess.DEVNULL,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OpenSSLVerificationError("OpenSSL executable is unavailable or timed out") from exc
    if result.returncode != 0:
        raise OpenSSLVerificationError("Could not determine OpenSSL version")
    version = (result.stdout or result.stderr).strip()
    match = re.search(r"OpenSSL\s+(\d+)\.", version)
    if not match:
        raise OpenSSLVerificationError("Unrecognized OpenSSL version output")
    return version, int(match.group(1))


def validate_x509_certificate(
    certificate_pem: bytes,
    *,
    policy: X509ValidationPolicy,
    openssl_binary: str = "openssl",
) -> X509ValidationResult:
    """Validate a single leaf certificate using OpenSSL and an explicit trust bundle.

    The verify_hostname and verify_ip options check peer identity separately
    from path validation. The selected purpose enforces TLS purpose/EKU policy.
    When a CRL bundle is supplied, CRL checking is enabled. If require_crl is
    true, absence of a CRL is rejected before invoking OpenSSL.
    """
    if not isinstance(certificate_pem, bytes) or not certificate_pem.strip():
        raise OpenSSLVerificationError("A non-empty X.509 certificate is required")
    if len(certificate_pem) > 1_048_576:
        raise OpenSSLVerificationError("Leaf certificate exceeds the 1 MiB input limit")
    if certificate_pem.count(b"-----BEGIN CERTIFICATE-----") > 1:
        raise OpenSSLVerificationError("Pass exactly one leaf certificate, not a PEM chain")
    try:
        if b"-----BEGIN CERTIFICATE-----" in certificate_pem:
            leaf = x509.load_pem_x509_certificate(certificate_pem)
        else:
            leaf = x509.load_der_x509_certificate(certificate_pem)
    except ValueError as exc:
        raise OpenSSLVerificationError("Malformed X.509 leaf certificate") from exc

    binary = shutil.which(openssl_binary)
    if binary is None:
        raise OpenSSLVerificationError("OpenSSL executable was not found on PATH")
    version, major = _openssl_version(binary, policy.timeout_seconds)

    cert_fp, spki_fp = certificate_fingerprints(certificate_pem)
    identity_checked = policy.expected_hostname or policy.expected_ip or ""
    with tempfile.TemporaryDirectory(prefix="node-pki-guard-") as temp_dir:
        leaf_file = _write_private_file(temp_dir, "leaf.pem", certificate_pem)
        ca_file = _write_private_file(temp_dir, "trusted-ca-bundle.pem", policy.ca_bundle_pem)
        command = [
            binary, "verify", "-verbose", "-show_chain",
            "-x509_strict", "-auth_level", str(policy.auth_level),
            "-verify_depth", str(policy.verify_depth),
            "-purpose", policy.purpose,
            "-CAfile", ca_file, "-no-CApath",
        ]
        # OpenSSL 3 adds a third implicit trust source. Disable it so that the
        # supplied CA bundle remains the only configured trust anchor source.
        if major >= 3:
            command.append("-no-CAstore")
        if policy.expected_hostname is not None:
            command.extend(["-verify_hostname", policy.expected_hostname.rstrip(".").encode("idna").decode("ascii")])
        else:
            command.extend(["-verify_ip", policy.expected_ip])
        if policy.intermediate_bundle_pem is not None:
            intermediate_file = _write_private_file(
                temp_dir, "untrusted-intermediates.pem", policy.intermediate_bundle_pem
            )
            command.extend(["-untrusted", intermediate_file])
        revocation_checked = policy.crl_bundle_pem is not None
        if policy.crl_bundle_pem is not None:
            crl_file = _write_private_file(temp_dir, "crl-bundle.pem", policy.crl_bundle_pem)
            command.extend(["-CRLfile", crl_file])
            command.append("-crl_check_all" if policy.check_all_crl else "-crl_check")
        command.append(leaf_file)
        try:
            result = subprocess.run(
                command, check=False, capture_output=True, text=True,
                timeout=policy.timeout_seconds, stdin=subprocess.DEVNULL,
                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"},
            )
        except subprocess.TimeoutExpired as exc:
            raise OpenSSLVerificationError("OpenSSL certificate verification timed out") from exc
        except OSError as exc:
            raise OpenSSLVerificationError("Could not execute OpenSSL verification") from exc
        output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
        if result.returncode != 0:
            raise OpenSSLVerificationError("OpenSSL certificate verification failed: " + output[-4000:])
    return X509ValidationResult(
        validated=True,
        certificate_fingerprint_sha256=cert_fp,
        spki_sha256=spki_fp,
        openssl_version=version,
        purpose=policy.purpose,
        identity_checked=identity_checked,
        revocation_checked=revocation_checked,
        verification_output=output,
    )
