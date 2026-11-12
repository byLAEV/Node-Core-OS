"""Constrained X.509 certificate issuance from a proof-of-possession CSR.

This module is a cryptographic issuance primitive, not a complete PKI service.
It deliberately does not authorize an operation, consume a UTXO, persist a
certificate, or create a signed administrative receipt. The caller must place
it behind the NODE-PKI-GUARD authorization/execution service before exposing
certificate issuance to an application or network interface.

The v1 issuer accepts one explicitly pinned, self-signed CA certificate and
only issues leaf certificates that match a caller-supplied issuance profile.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import ipaddress
import re
from typing import Any

from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from cryptography.x509.oid import ObjectIdentifier

from node_core.security.node_pki_guard import (
    NodePKIGuardError,
    certificate_fingerprints,
    public_key_spki_sha256,
)


HEX_32 = re.compile(r"^[0-9a-f]{64}$")
PROFILE_ID = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,63}$")
DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
RSA_SHA2_OIDS = {
    "1.2.840.113549.1.1.11",  # sha256WithRSAEncryption
    "1.2.840.113549.1.1.12",  # sha384WithRSAEncryption
    "1.2.840.113549.1.1.13",  # sha512WithRSAEncryption
}
ECDSA_SHA2_OIDS = {
    "1.2.840.10045.4.3.2",  # ecdsa-with-SHA256
    "1.2.840.10045.4.3.3",  # ecdsa-with-SHA384
    "1.2.840.10045.4.3.4",  # ecdsa-with-SHA512
}
ED25519_OID = "1.3.101.112"
SERVER_AUTH_OID = "1.3.6.1.5.5.7.3.1"


class X509IssuanceError(NodePKIGuardError):
    """Base error for a rejected CSR, profile, issuer, or issuance request."""


class CSRValidationError(X509IssuanceError):
    """Raised when a CSR is malformed or violates the selected profile."""


class IssuerConfigurationError(X509IssuanceError):
    """Raised when the pinned CA certificate or its private key is not valid."""


@dataclass(frozen=True)
class X509IssuanceProfile:
    """Allowlist profile for a leaf certificate.

    DNS names must equal one of allowed_dns_suffixes or be a subdomain of it.
    IP SANs are rejected unless allow_ip_sans is explicitly enabled.
    CSR extensions other than SubjectAlternativeName are never copied.
    """

    profile_id: str
    profile_version: str
    allowed_dns_suffixes: tuple[str, ...]
    validity_days: int = 30
    not_before_skew_seconds: int = 300
    allow_ip_sans: bool = False
    extended_key_usage_oids: tuple[str, ...] = (SERVER_AUTH_OID,)
    key_usage: tuple[str, ...] = ("digital_signature",)

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not PROFILE_ID.fullmatch(self.profile_id):
            raise ValueError("profile_id must be an uppercase identifier of at most 64 characters")
        if not isinstance(self.profile_version, str) or not self.profile_version.strip():
            raise ValueError("profile_version is required")
        if type(self.validity_days) is not int or not 1 <= self.validity_days <= 397:
            raise ValueError("validity_days must be an integer from 1 through 397")
        if (type(self.not_before_skew_seconds) is not int
                or not 0 <= self.not_before_skew_seconds <= 600):
            raise ValueError("not_before_skew_seconds must be from 0 through 600")
        if type(self.allow_ip_sans) is not bool:
            raise ValueError("allow_ip_sans must be a boolean")

        if not isinstance(self.allowed_dns_suffixes, tuple):
            raise ValueError("allowed_dns_suffixes must be a tuple")
        normalized_suffixes = tuple(_normalize_dns_name(item) for item in self.allowed_dns_suffixes)
        if len(set(normalized_suffixes)) != len(normalized_suffixes):
            raise ValueError("allowed_dns_suffixes cannot contain duplicates")
        if not normalized_suffixes and not self.allow_ip_sans:
            raise ValueError("At least one DNS suffix or explicit IP SAN permission is required")
        object.__setattr__(self, "allowed_dns_suffixes", normalized_suffixes)

        if not isinstance(self.extended_key_usage_oids, tuple) or not self.extended_key_usage_oids:
            raise ValueError("extended_key_usage_oids must be a non-empty tuple")
        try:
            for oid in self.extended_key_usage_oids:
                if not isinstance(oid, str) or not oid:
                    raise ValueError("Extended Key Usage OIDs must be non-empty strings")
                ObjectIdentifier(oid)
        except ValueError as exc:
            raise ValueError("Invalid Extended Key Usage object identifier") from exc
        if len(set(self.extended_key_usage_oids)) != len(self.extended_key_usage_oids):
            raise ValueError("Extended Key Usage OIDs cannot contain duplicates")

        allowed_usage = {
            "digital_signature", "content_commitment", "key_encipherment",
            "data_encipherment", "key_agreement",
        }
        if not isinstance(self.key_usage, tuple) or not self.key_usage:
            raise ValueError("key_usage must be a non-empty tuple")
        if len(set(self.key_usage)) != len(self.key_usage):
            raise ValueError("key_usage cannot contain duplicates")
        if any(item not in allowed_usage for item in self.key_usage):
            raise ValueError("key_usage contains an unsupported leaf key usage")
        if "digital_signature" not in self.key_usage:
            raise ValueError("v1 leaf profiles must require digital_signature")


@dataclass(frozen=True)
class IssuedX509Certificate:
    """Certificate bytes and the profile metadata used to create them."""

    certificate_pem: bytes
    serial_number: int
    certificate_fingerprint_sha256: str
    spki_sha256: str
    issuer_fingerprint_sha256: str
    issuer_key_id: str
    profile_id: str
    profile_version: str
    not_valid_before_epoch: int
    not_valid_after_epoch: int


def _normalize_dns_name(value: str) -> str:
    if not isinstance(value, str) or not value or value.endswith(".") or "*" in value:
        raise ValueError("DNS names must be non-empty, absolute-free names without wildcards")
    try:
        ascii_name = value.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("DNS name is not valid IDNA") from exc
    if len(ascii_name) > 253:
        raise ValueError("DNS name exceeds 253 characters")
    labels = ascii_name.split(".")
    if any(not DNS_LABEL.fullmatch(label) for label in labels):
        raise ValueError("DNS name contains an invalid label")
    return ascii_name


def _validate_public_key(public_key: Any, *, role: str) -> None:
    if isinstance(public_key, rsa.RSAPublicKey):
        if public_key.key_size < 2048:
            raise X509IssuanceError(role + " RSA key must be at least 2048 bits")
        return
    if isinstance(public_key, ec.EllipticCurvePublicKey):
        if not isinstance(public_key.curve, (ec.SECP256R1, ec.SECP384R1, ec.SECP521R1)):
            raise X509IssuanceError(role + " EC key must use P-256, P-384, or P-521")
        return
    if isinstance(public_key, ed25519.Ed25519PublicKey):
        return
    raise X509IssuanceError(role + " public key algorithm is not permitted by v1")


def _load_single_pem_certificate(certificate_pem: bytes) -> x509.Certificate:
    if not isinstance(certificate_pem, bytes) or not certificate_pem.strip():
        raise IssuerConfigurationError("A non-empty issuer certificate PEM is required")
    if certificate_pem.count(b"-----BEGIN CERTIFICATE-----") != 1:
        raise IssuerConfigurationError("Provide exactly one issuer certificate PEM")
    try:
        return x509.load_pem_x509_certificate(certificate_pem)
    except ValueError as exc:
        raise IssuerConfigurationError("Issuer certificate PEM is malformed") from exc


def _verify_self_signed_ca_signature(certificate: x509.Certificate) -> None:
    public_key = certificate.public_key()
    oid = certificate.signature_algorithm_oid.dotted_string
    try:
        if isinstance(public_key, rsa.RSAPublicKey):
            if oid not in RSA_SHA2_OIDS:
                raise IssuerConfigurationError("Pinned RSA CA must use SHA-256, SHA-384, or SHA-512 with PKCS#1 v1.5")
            public_key.verify(
                certificate.signature,
                certificate.tbs_certificate_bytes,
                padding.PKCS1v15(),
                certificate.signature_hash_algorithm,
            )
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            if oid not in ECDSA_SHA2_OIDS:
                raise IssuerConfigurationError("Pinned EC CA must use ECDSA with SHA-256, SHA-384, or SHA-512")
            public_key.verify(
                certificate.signature,
                certificate.tbs_certificate_bytes,
                ec.ECDSA(certificate.signature_hash_algorithm),
            )
        elif isinstance(public_key, ed25519.Ed25519PublicKey):
            if oid != ED25519_OID:
                raise IssuerConfigurationError("Pinned Ed25519 CA has an unexpected signature algorithm")
            public_key.verify(certificate.signature, certificate.tbs_certificate_bytes)
        else:
            raise IssuerConfigurationError("Pinned CA public key algorithm is not supported")
    except (InvalidSignature, UnsupportedAlgorithm, ValueError) as exc:
        raise IssuerConfigurationError("Pinned CA certificate is not correctly self-signed") from exc


def _load_and_validate_issuer(
    *,
    issuer_certificate_pem: bytes,
    issuer_private_key_pem: bytes,
    issuer_private_key_password: bytes | None,
    trusted_issuer_fingerprint_sha256: str,
    now_utc: datetime,
) -> tuple[x509.Certificate, Any, str, str]:
    if not isinstance(trusted_issuer_fingerprint_sha256, str) or not HEX_32.fullmatch(
        trusted_issuer_fingerprint_sha256
    ):
        raise IssuerConfigurationError("An explicit lowercase SHA-256 CA fingerprint pin is required")
    issuer_certificate = _load_single_pem_certificate(issuer_certificate_pem)
    issuer_fingerprint = issuer_certificate.fingerprint(hashes.SHA256()).hex()
    if issuer_fingerprint != trusted_issuer_fingerprint_sha256:
        raise IssuerConfigurationError("Issuer certificate does not match the configured trust pin")

    try:
        constraints = issuer_certificate.extensions.get_extension_for_class(
            x509.BasicConstraints
        ).value
        key_usage = issuer_certificate.extensions.get_extension_for_class(
            x509.KeyUsage
        ).value
    except x509.ExtensionNotFound as exc:
        raise IssuerConfigurationError("CA certificate must contain BasicConstraints and KeyUsage") from exc
    if not constraints.ca or not key_usage.key_cert_sign:
        raise IssuerConfigurationError("Pinned issuer is not authorized to sign certificates")
    if issuer_certificate.subject != issuer_certificate.issuer:
        raise IssuerConfigurationError("v1 requires a pinned self-signed CA trust anchor")
    _validate_public_key(issuer_certificate.public_key(), role="CA")
    _verify_self_signed_ca_signature(issuer_certificate)

    if not isinstance(issuer_private_key_pem, bytes) or not issuer_private_key_pem:
        raise IssuerConfigurationError("Issuer private key PEM is required")
    if issuer_private_key_password is not None and not isinstance(issuer_private_key_password, bytes):
        raise IssuerConfigurationError("Issuer private key password must be bytes")
    try:
        private_key = serialization.load_pem_private_key(
            issuer_private_key_pem,
            password=issuer_private_key_password,
        )
    except (TypeError, ValueError, UnsupportedAlgorithm) as exc:
        raise IssuerConfigurationError("Issuer private key could not be loaded") from exc
    _validate_public_key(private_key.public_key(), role="CA private")
    if public_key_spki_sha256(private_key.public_key()) != public_key_spki_sha256(
        issuer_certificate.public_key()
    ):
        raise IssuerConfigurationError("Issuer private key does not match the pinned CA certificate")

    if now_utc < issuer_certificate.not_valid_before_utc:
        raise IssuerConfigurationError("Pinned CA certificate is not yet valid")
    if now_utc >= issuer_certificate.not_valid_after_utc:
        raise IssuerConfigurationError("Pinned CA certificate has expired")

    issuer_key_id = public_key_spki_sha256(issuer_certificate.public_key())
    return issuer_certificate, private_key, issuer_fingerprint, issuer_key_id


def _validate_csr_and_extract_san(
    csr_pem: bytes,
    profile: X509IssuanceProfile,
) -> tuple[x509.CertificateSigningRequest, x509.SubjectAlternativeName]:
    if not isinstance(csr_pem, bytes) or not csr_pem.strip():
        raise CSRValidationError("A non-empty PKCS#10 CSR PEM is required")
    if csr_pem.count(b"-----BEGIN CERTIFICATE REQUEST-----") != 1:
        raise CSRValidationError("Provide exactly one PKCS#10 CSR PEM")
    try:
        csr = x509.load_pem_x509_csr(csr_pem)
    except ValueError as exc:
        raise CSRValidationError("CSR PEM is malformed") from exc
    if not csr.is_signature_valid:
        raise CSRValidationError("CSR proof-of-possession signature is invalid")
    if len(csr.subject) == 0:
        raise CSRValidationError("CSR subject must not be empty")
    _validate_public_key(csr.public_key(), role="CSR")

    if len(csr.extensions) != 1 or not isinstance(
        csr.extensions[0].value, x509.SubjectAlternativeName
    ):
        raise CSRValidationError("v1 CSR must request only one SubjectAlternativeName extension")
    san = csr.extensions[0].value
    if not san:
        raise CSRValidationError("CSR SubjectAlternativeName must not be empty")

    normalized_names: list[x509.GeneralName] = []
    seen: set[tuple[str, str]] = set()
    for general_name in san:
        if isinstance(general_name, x509.DNSName):
            try:
                dns_name = _normalize_dns_name(general_name.value)
            except ValueError as exc:
                raise CSRValidationError(str(exc)) from exc
            if not any(
                dns_name == suffix or dns_name.endswith("." + suffix)
                for suffix in profile.allowed_dns_suffixes
            ):
                raise CSRValidationError("CSR DNS SAN is outside the issuance profile allowlist")
            key = ("DNS", dns_name)
            normalized_names.append(x509.DNSName(dns_name))
        elif isinstance(general_name, x509.IPAddress):
            if not profile.allow_ip_sans:
                raise CSRValidationError("IP SANs are not permitted by this issuance profile")
            if not isinstance(general_name.value, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
                raise CSRValidationError("IP SAN must contain an address, not a network")
            key = ("IP", str(general_name.value))
            normalized_names.append(x509.IPAddress(general_name.value))
        else:
            raise CSRValidationError("v1 permits only DNS and explicitly enabled IP SAN values")
        if key in seen:
            raise CSRValidationError("CSR SubjectAlternativeName contains a duplicate value")
        seen.add(key)

    normalized_names.sort(key=lambda item: (type(item).__name__, str(item.value)))
    return csr, x509.SubjectAlternativeName(normalized_names)


def _key_usage_extension(profile: X509IssuanceProfile) -> x509.KeyUsage:
    usages = set(profile.key_usage)
    key_agreement = "key_agreement" in usages
    return x509.KeyUsage(
        digital_signature="digital_signature" in usages,
        content_commitment="content_commitment" in usages,
        key_encipherment="key_encipherment" in usages,
        data_encipherment="data_encipherment" in usages,
        key_agreement=key_agreement,
        key_cert_sign=False,
        crl_sign=False,
        encipher_only=False if key_agreement else None,
        decipher_only=False if key_agreement else None,
    )


def _signing_hash(private_key: Any) -> hashes.HashAlgorithm | None:
    if isinstance(private_key, ed25519.Ed25519PrivateKey):
        return None
    if isinstance(private_key, (rsa.RSAPrivateKey, ec.EllipticCurvePrivateKey)):
        return hashes.SHA256()
    raise IssuerConfigurationError("CA private key algorithm is not supported")


def issue_x509_certificate(
    *,
    csr_pem: bytes,
    issuer_certificate_pem: bytes,
    issuer_private_key_pem: bytes,
    trusted_issuer_fingerprint_sha256: str,
    profile: X509IssuanceProfile,
    issuer_private_key_password: bytes | None = None,
    now_utc: datetime | None = None,
) -> IssuedX509Certificate:
    """Issue one constrained leaf certificate after validating the CSR and CA.

    Security boundary: this function performs X.509 issuance only. It does not
    consume or verify a NODE-PKI-GUARD UTXO authorization. Do not expose it to
    callers until an application service has validated the binding, operation,
    proof requirements and policy, consumed the matching authorization through
    consume_authorization(), and established durable operation recovery.
    """
    if not isinstance(profile, X509IssuanceProfile):
        raise ValueError("A validated X509IssuanceProfile is required")
    current_time = datetime.now(timezone.utc) if now_utc is None else now_utc
    if not isinstance(current_time, datetime) or current_time.tzinfo is None:
        raise ValueError("now_utc must be a timezone-aware datetime")
    current_time = current_time.astimezone(timezone.utc)

    issuer_certificate, issuer_private_key, issuer_fingerprint, issuer_key_id = (
        _load_and_validate_issuer(
            issuer_certificate_pem=issuer_certificate_pem,
            issuer_private_key_pem=issuer_private_key_pem,
            issuer_private_key_password=issuer_private_key_password,
            trusted_issuer_fingerprint_sha256=trusted_issuer_fingerprint_sha256,
            now_utc=current_time,
        )
    )
    csr, san = _validate_csr_and_extract_san(csr_pem, profile)

    not_before = max(
        current_time - timedelta(seconds=profile.not_before_skew_seconds),
        issuer_certificate.not_valid_before_utc,
    )
    not_after = min(
        current_time + timedelta(days=profile.validity_days),
        issuer_certificate.not_valid_after_utc,
    )
    if not_after <= not_before:
        raise IssuerConfigurationError("CA validity window is too short to issue this certificate")

    builder = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(issuer_certificate.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before.replace(tzinfo=None))
        .not_valid_after(not_after.replace(tzinfo=None))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(_key_usage_extension(profile), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ObjectIdentifier(oid) for oid in profile.extended_key_usage_oids]),
            critical=False,
        )
        .add_extension(san, critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(csr.public_key()), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_certificate.public_key()),
            critical=False,
        )
    )
    try:
        certificate = builder.sign(
            private_key=issuer_private_key,
            algorithm=_signing_hash(issuer_private_key),
        )
    except (TypeError, ValueError, UnsupportedAlgorithm) as exc:
        raise IssuerConfigurationError("CA failed to sign the X.509 certificate") from exc

    certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)
    certificate_fingerprint, spki_fingerprint = certificate_fingerprints(certificate_pem)
    return IssuedX509Certificate(
        certificate_pem=certificate_pem,
        serial_number=certificate.serial_number,
        certificate_fingerprint_sha256=certificate_fingerprint,
        spki_sha256=spki_fingerprint,
        issuer_fingerprint_sha256=issuer_fingerprint,
        issuer_key_id=issuer_key_id,
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        not_valid_before_epoch=int(certificate.not_valid_before_utc.timestamp()),
        not_valid_after_epoch=int(certificate.not_valid_after_utc.timestamp()),
    )
