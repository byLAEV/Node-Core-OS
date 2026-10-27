"""Interop profile for standard HTTPS certificates bound to Node Core OS identities.

This module does not issue public Web PKI certificates and does not replace TLS
certificate-chain validation. The operating system/browser validates the public
certificate chain; this module adds a signed, portable link to a Node Core OS node.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.x509.oid import ExtendedKeyUsageOID

from node_core.identity.node_identity import NodeIdentityStore


class WebTLSProfileError(ValueError):
    """Raised when a web certificate or its Node Core OS binding is invalid."""


def _canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _normalize_dns_name(dns_name: str) -> str:
    if not isinstance(dns_name, str):
        raise WebTLSProfileError("DNS name must be text.")
    name = dns_name.rstrip(".").lower()
    if not name or len(name) > 253 or "*" in name:
        raise WebTLSProfileError("A concrete DNS name is required; wildcards are not accepted in bindings.")
    labels = name.split(".")
    if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
        raise WebTLSProfileError("DNS name contains an invalid label.")
    return name


def _load_and_validate_certificate(certificate_pem: bytes, dns_name: str, now: datetime) -> x509.Certificate:
    if not isinstance(certificate_pem, bytes):
        raise WebTLSProfileError("Certificate must be PEM bytes.")
    try:
        cert = x509.load_pem_x509_certificate(certificate_pem)
    except (ValueError, TypeError) as exc:
        raise WebTLSProfileError("Certificate PEM is malformed.") from exc

    if now < cert.not_valid_before_utc or now > cert.not_valid_after_utc:
        raise WebTLSProfileError("Web certificate is outside its validity period.")

    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound as exc:
        raise WebTLSProfileError("Web certificate must contain a Subject Alternative Name.") from exc

    expected_dns = _normalize_dns_name(dns_name)
    certificate_dns = {name.rstrip(".").lower() for name in san.get_values_for_type(x509.DNSName)}
    if expected_dns not in certificate_dns:
        raise WebTLSProfileError("Certificate SAN does not contain the exact requested DNS name.")

    try:
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    except x509.ExtensionNotFound as exc:
        raise WebTLSProfileError("Web certificate must explicitly contain serverAuth EKU.") from exc
    if ExtendedKeyUsageOID.SERVER_AUTH not in eku:
        raise WebTLSProfileError("Certificate is not authorized for TLS server authentication.")

    try:
        key_usage = cert.extensions.get_extension_for_class(x509.KeyUsage).value
    except x509.ExtensionNotFound:
        key_usage = None
    if key_usage is not None and not key_usage.digital_signature:
        raise WebTLSProfileError("TLS server certificate KeyUsage must permit digital signatures.")

    return cert


def create_web_certificate_binding(
    identity_store: NodeIdentityStore,
    certificate_pem: bytes,
    dns_name: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Sign a deterministic binding between a node identity, DNS name and HTTPS certificate.

    The HTTPS certificate must already have been issued by the relevant Web PKI
    or private CA. This function does not issue certificates or validate a CA chain.
    """
    metadata = identity_store.load()
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise WebTLSProfileError("The supplied validation time must be timezone-aware.")
    dns_name = _normalize_dns_name(dns_name)
    cert = _load_and_validate_certificate(certificate_pem, dns_name, instant)
    binding: dict[str, Any] = {
        "schema_version": 1,
        "profile": "NODE_CORE_OS_WEB_TLS_BINDING",
        "signature_algorithm": "Ed25519",
        "node_id": metadata["node_id"],
        "node_public_key": metadata["public_key"],
        "dns_name": dns_name,
        "certificate_sha256": hashlib.sha256(certificate_pem).hexdigest(),
        "certificate_not_before": cert.not_valid_before_utc.isoformat(),
        "certificate_not_after": cert.not_valid_after_utc.isoformat(),
    }
    signature = identity_store.sign(_canonical_json(binding))
    binding["signature"] = base64.b64encode(signature).decode("ascii")
    return binding


def verify_web_certificate_binding(
    binding: dict[str, Any],
    certificate_pem: bytes,
    expected_dns_name: str,
    *,
    now: datetime | None = None,
) -> bool:
    """Verify binding signature, node ID, DNS SAN, certificate fingerprint and validity."""
    try:
        if not isinstance(binding, dict):
            return False
        if binding.get("schema_version") != 1 or binding.get("profile") != "NODE_CORE_OS_WEB_TLS_BINDING":
            return False
        if binding.get("signature_algorithm") != "Ed25519":
            return False
        public_hex = binding["node_public_key"]
        node_id = binding["node_id"]
        public_bytes = bytes.fromhex(public_hex)
        public_key = Ed25519PublicKey.from_public_bytes(public_bytes)
        expected_node_id = "sha256:" + hashlib.sha256(public_bytes).hexdigest()
        if node_id != expected_node_id:
            return False

        signature = base64.b64decode(binding["signature"], validate=True)
        unsigned = {key: value for key, value in binding.items() if key != "signature"}
        public_key.verify(signature, _canonical_json(unsigned))

        dns_name = _normalize_dns_name(expected_dns_name)
        if binding.get("dns_name") != dns_name:
            return False
        instant = now or datetime.now(timezone.utc)
        if instant.tzinfo is None:
            return False
        cert = _load_and_validate_certificate(certificate_pem, dns_name, instant)
        if hashlib.sha256(certificate_pem).hexdigest() != binding.get("certificate_sha256"):
            return False
        if cert.not_valid_before_utc.isoformat() != binding.get("certificate_not_before"):
            return False
        if cert.not_valid_after_utc.isoformat() != binding.get("certificate_not_after"):
            return False
        return True
    except (KeyError, TypeError, ValueError, InvalidSignature, WebTLSProfileError, x509.DuplicateExtension):
        return False
