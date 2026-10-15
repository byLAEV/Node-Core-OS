"""TLS 1.3 transport pinned to Node Core OS Ed25519 identities.

Certificates are self-signed by the existing node identity key. Each endpoint
must explicitly trust the peer certificate PEM before connecting. TLS verifies
the pinned certificate; this module additionally checks that the certificate's
Ed25519 public key derives the expected Node Core OS node ID.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import ssl
from typing import Iterable

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.x509.oid import NameOID

from node_core.identity.node_identity import NodeIdentityError, NodeIdentityStore


class TLSTransportError(RuntimeError):
    """Raised when TLS setup or pinned peer identity verification fails."""


class NodeTLSTransport:
    """Build TLS 1.3 contexts and validate peers against pinned node certificates."""

    def __init__(self, identity_store: NodeIdentityStore) -> None:
        self.identity_store = identity_store
        self.certificate_path = identity_store.identity_dir / "node-cert.pem"

    def ensure_certificate(self) -> bytes:
        """Create or validate a self-signed certificate using the node's existing key."""
        try:
            metadata = self.identity_store.load()
            if self.certificate_path.exists():
                pem = self.certificate_path.read_bytes()
                cert = x509.load_pem_x509_certificate(pem)
                self._validate_certificate(cert, metadata["node_id"], metadata["public_key"])
                return pem

            private_key = serialization.load_pem_private_key(
                self.identity_store.private_key_path.read_bytes(), password=None
            )
            if not isinstance(private_key, Ed25519PrivateKey):
                raise TLSTransportError("Node private key is not Ed25519.")
            # Every self-signed peer certificate must have a unique subject.
            # OpenSSL can otherwise select the wrong trust anchor when several
            # pinned certificates share the same subject, rejecting valid peers.
            subject = issuer = x509.Name([
                x509.NameAttribute(
                    NameOID.COMMON_NAME,
                    "Node Core OS P2P " + metadata["node_id"],
                )
            ])
            now = datetime.now(timezone.utc)
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(minutes=5))
                .not_valid_after(now + timedelta(days=365))
                .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                .add_extension(
                    x509.SubjectAlternativeName([
                        x509.UniformResourceIdentifier("urn:node-core-os:node:" + metadata["node_id"])
                    ]),
                    critical=False,
                )
                .sign(private_key, algorithm=None)
            )
            pem = cert.public_bytes(serialization.Encoding.PEM)
            self._write_private_certificate(pem)
            self._validate_certificate(x509.load_pem_x509_certificate(pem), metadata["node_id"], metadata["public_key"])
            return pem
        except (OSError, ValueError, TypeError, NodeIdentityError) as exc:
            if isinstance(exc, TLSTransportError):
                raise
            raise TLSTransportError("Unable to create or load the node TLS certificate.") from exc

    def server_context(self, trusted_peer_certificates: Iterable[bytes]) -> ssl.SSLContext:
        """Build a TLS server context requiring a certificate from a pinned peer."""
        context = self._base_context(server_side=True)
        context.load_cert_chain(str(self.certificate_path), str(self.identity_store.private_key_path))
        self._load_pinned_certificates(context, trusted_peer_certificates)
        context.verify_mode = ssl.CERT_REQUIRED
        return context

    def client_context(self, trusted_peer_certificates: Iterable[bytes]) -> ssl.SSLContext:
        """Build a TLS client context requiring a pinned server and presenting this node."""
        context = self._base_context(server_side=False)
        context.check_hostname = False
        context.load_cert_chain(str(self.certificate_path), str(self.identity_store.private_key_path))
        self._load_pinned_certificates(context, trusted_peer_certificates)
        context.verify_mode = ssl.CERT_REQUIRED
        return context

    @staticmethod
    def verify_peer_identity(
        tls_socket: ssl.SSLSocket, expected_node_id: str | None = None
    ) -> dict[str, str]:
        """Verify the TLS peer certificate key derives the expected node ID."""
        pem = tls_socket.getpeercert(binary_form=True)
        if not pem:
            raise TLSTransportError("TLS peer did not present a certificate.")
        try:
            cert = x509.load_der_x509_certificate(pem)
            public_key = cert.public_key()
            if not isinstance(public_key, Ed25519PublicKey):
                raise TLSTransportError("TLS peer certificate does not use Ed25519.")
            raw_key = public_key.public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
            node_id = "sha256:" + hashlib.sha256(raw_key).hexdigest()
            if expected_node_id is not None and node_id != expected_node_id:
                raise TLSTransportError("TLS peer certificate does not match the expected node ID.")
            return {"node_id": node_id, "public_key": raw_key.hex()}
        except (ValueError, TypeError) as exc:
            raise TLSTransportError("TLS peer certificate is malformed.") from exc

    @staticmethod
    def _base_context(server_side: bool) -> ssl.SSLContext:
        protocol = ssl.PROTOCOL_TLS_SERVER if server_side else ssl.PROTOCOL_TLS_CLIENT
        context = ssl.SSLContext(protocol)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        return context

    @staticmethod
    def _load_pinned_certificates(context: ssl.SSLContext, certificates: Iterable[bytes]) -> None:
        pem_list = list(certificates)
        if not pem_list or any(not isinstance(item, bytes) or b"-----BEGIN CERTIFICATE-----" not in item for item in pem_list):
            raise TLSTransportError("At least one valid pinned peer certificate PEM is required.")
        try:
            context.load_verify_locations(cadata=b"\n".join(pem_list).decode("ascii"))
        except (ssl.SSLError, UnicodeError) as exc:
            raise TLSTransportError("Unable to load pinned peer certificates.") from exc

    def _validate_certificate(self, cert: x509.Certificate, node_id: str, public_key_hex: str) -> None:
        public_key = cert.public_key()
        if not isinstance(public_key, Ed25519PublicKey):
            raise TLSTransportError("Stored TLS certificate does not use Ed25519.")
        raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        if raw.hex() != public_key_hex:
            raise TLSTransportError("TLS certificate public key differs from the node identity.")
        if "sha256:" + hashlib.sha256(raw).hexdigest() != node_id:
            raise TLSTransportError("TLS certificate node ID does not match the identity.")

    def _write_private_certificate(self, pem: bytes) -> None:
        self.identity_store.identity_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = self.certificate_path
        descriptor = None
        try:
            import os
            import tempfile
            descriptor, temporary = tempfile.mkstemp(prefix=".node-cert-", suffix=".tmp", dir=path.parent)
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None
                handle.write(pem)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            os.chmod(path, 0o600)
        finally:
            if descriptor is not None:
                import os
                os.close(descriptor)
