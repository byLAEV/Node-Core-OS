"""Durable Standalone NODE-PKI-GUARD certificate lifecycle orchestration.

The service stages the exact X.509 certificate before consuming the UTXO. This
ordering makes retries safe across process restarts: the same idempotency key
reuses the same staged certificate and the backend's durable spend result.
SQLite state is local ACID only; it is not distributed consensus.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Iterator, Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa

from node_core.security.node_pki_guard import AuthorizationDecision, NodePKIGuardError
from node_core.security.node_pki_guard_backend import (
    CommitKind,
    SpendRequest,
    UTXOAuthorizationBackend,
    compute_spend_request_hash,
)
from node_core.security.node_pki_guard_issuer import (
    IssuedX509Certificate,
    X509IssuanceProfile,
    issue_x509_certificate,
)
from node_core.security.node_pki_guard_utxo import consume_authorization


class LifecycleError(NodePKIGuardError):
    """Lifecycle operation was rejected or could not be safely completed."""


@dataclass(frozen=True)
class LifecycleResult:
    operation_id: str
    idempotency_key: str
    state: str
    certificate_pem: bytes
    certificate_fingerprint_sha256: str
    receipt: dict[str, Any]
    receipt_signature: str
    commit_kind: str
    transaction_id: str


class PKILifecycleService:
    """Orchestrate staged X.509 issuance, one UTXO spend and a signed receipt.

    Callers MUST supply an AuthorizationDecision created by the trusted policy
    validation path. This class independently checks its operation hash,
    authorization ID and outpoint against the immutable SpendRequest, and
    checks the backend commit evidence before marking an operation COMMITTED.
    """

    SCHEMA_VERSION = 2

    def __init__(
        self,
        *,
        db_path: str | Path,
        backend: UTXOAuthorizationBackend,
        issuer_certificate_pem: bytes,
        issuer_private_key_pem: bytes,
        trusted_issuer_fingerprint_sha256: str,
        profile: X509IssuanceProfile,
        issuer_private_key_password: bytes | None = None,
        receipt_signing_key_pem: bytes,
        receipt_key_id: str,
        receipt_signing_key_password: bytes | None = None,
    ) -> None:
        self.db_path = str(Path(db_path).expanduser())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.backend = backend
        self.issuer_certificate_pem = issuer_certificate_pem
        self.issuer_private_key_pem = issuer_private_key_pem
        self.trusted_issuer_fingerprint_sha256 = trusted_issuer_fingerprint_sha256
        self.profile = profile
        self.issuer_private_key_password = issuer_private_key_password
        if not isinstance(receipt_signing_key_pem, bytes) or not receipt_signing_key_pem:
            raise ValueError("A dedicated receipt signing private key PEM is required")
        if not isinstance(receipt_key_id, str) or not receipt_key_id.strip():
            raise ValueError("receipt_key_id is required")
        self.receipt_signing_key_pem = receipt_signing_key_pem
        self.receipt_key_id = receipt_key_id
        self.receipt_signing_key_password = receipt_signing_key_password
        try:
            ca_key = serialization.load_pem_private_key(
                issuer_private_key_pem, password=issuer_private_key_password
            )
            receipt_key = serialization.load_pem_private_key(
                receipt_signing_key_pem, password=receipt_signing_key_password
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("CA or receipt signing key could not be loaded") from exc
        ca_spki = ca_key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        receipt_spki = receipt_key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        if ca_spki == receipt_spki:
            raise ValueError("Receipt signing key MUST be distinct from the CA private key")
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=10.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 10000")
            yield conn
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._connection() as conn:
            mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if str(mode).lower() != "wal":
                raise LifecycleError("Lifecycle store could not enable WAL mode")
            conn.execute("PRAGMA synchronous=FULL")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS lifecycle_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lifecycle_operations (
                    idempotency_key TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL UNIQUE,
                    request_hash TEXT NOT NULL,
                    csr_sha256 TEXT,
                    operation_hash TEXT NOT NULL,
                    authorization_id TEXT NOT NULL,
                    outpoint TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('PREPARED','COMMITTED')),
                    certificate_pem BLOB NOT NULL,
                    certificate_fingerprint_sha256 TEXT NOT NULL,
                    receipt_json TEXT,
                    receipt_signature TEXT,
                    transaction_id TEXT,
                    commit_kind TEXT,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );
            """)
            conn.execute(
                "INSERT OR IGNORE INTO lifecycle_metadata(key,value) VALUES('schema_version','1')"
            )
            columns = {
                row["name"] for row in conn.execute(
                    "PRAGMA table_info(lifecycle_operations)"
                ).fetchall()
            }
            if "csr_sha256" not in columns:
                conn.execute("ALTER TABLE lifecycle_operations ADD COLUMN csr_sha256 TEXT")
            version = conn.execute(
                "SELECT value FROM lifecycle_metadata WHERE key='schema_version'"
            ).fetchone()
            if version is None or int(version["value"]) > self.SCHEMA_VERSION:
                raise LifecycleError("Unsupported lifecycle store schema version")
            conn.execute(
                "UPDATE lifecycle_metadata SET value=? WHERE key='schema_version'",
                (str(self.SCHEMA_VERSION),),
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")

    @staticmethod
    def _sign_receipt(payload: dict[str, Any], private_key_pem: bytes,
                      password: bytes | None) -> str:
        key = serialization.load_pem_private_key(private_key_pem, password=password)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("utf-8")
        if isinstance(key, ed25519.Ed25519PrivateKey):
            signature = key.sign(encoded)
        elif isinstance(key, rsa.RSAPrivateKey):
            signature = key.sign(encoded, padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=hashes.SHA256().digest_size), hashes.SHA256())
        elif isinstance(key, ec.EllipticCurvePrivateKey):
            signature = key.sign(encoded, ec.ECDSA(hashes.SHA256()))
        else:
            raise LifecycleError("Unsupported CA receipt-signing key algorithm")
        import base64
        return base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")

    def _load(self, idempotency_key: str) -> sqlite3.Row | None:
        with self._connection() as conn:
            return conn.execute(
                "SELECT * FROM lifecycle_operations WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()

    def _issue_prevalidated(
        self,
        *,
        decision: AuthorizationDecision,
        request: SpendRequest,
        csr_pem: bytes,
        finality_timeout_seconds: float = 60.0,
    ) -> LifecycleResult:
        if decision.decision != "PROTECTED":
            raise LifecycleError("Only a PROTECTED policy decision may issue a certificate")
        if not 0 < finality_timeout_seconds <= 3600:
            raise ValueError("finality_timeout_seconds must be between 0 and 3600")
        expected_hash = compute_spend_request_hash(
            operation_id=request.operation_id,
            idempotency_key=request.idempotency_key,
            operation_hash=request.operation_hash,
            authorization_id=request.authorization_id,
            outpoint=request.outpoint,
            binding_id=request.binding_id,
            node_id=request.node_id,
            owner_key_id=request.owner_key_id,
            policy_id=request.policy_id,
            policy_version=request.policy_version,
            fee_amount=request.fee_amount,
            fee_asset=request.fee_asset,
        )
        if request.request_hash != expected_hash:
            raise LifecycleError("Spend request hash does not match immutable request content")
        if (decision.operation_hash != request.operation_hash
                or decision.authorization_id != request.authorization_id
                or decision.outpoint != request.outpoint):
            raise LifecycleError("Policy decision does not match the spend request")

        csr_sha256 = hashlib.sha256(csr_pem).hexdigest()
        row = self._load(request.idempotency_key)
        if row is not None:
            if (row["request_hash"] != request.request_hash
                    or row["operation_id"] != request.operation_id
                    or row["authorization_id"] != request.authorization_id
                    or row["outpoint"] != request.outpoint
                    or row["csr_sha256"] != csr_sha256):
                raise LifecycleError("Idempotency key was reused with different CSR or operation content")
            if row["state"] == "COMMITTED":
                return self._result(row)
            certificate_pem = bytes(row["certificate_pem"])
            certificate_fp = row["certificate_fingerprint_sha256"]
        else:
            issued: IssuedX509Certificate = issue_x509_certificate(
                csr_pem=csr_pem,
                issuer_certificate_pem=self.issuer_certificate_pem,
                issuer_private_key_pem=self.issuer_private_key_pem,
                issuer_private_key_password=self.issuer_private_key_password,
                trusted_issuer_fingerprint_sha256=self.trusted_issuer_fingerprint_sha256,
                profile=self.profile,
            )
            certificate_pem = issued.certificate_pem
            certificate_fp = issued.certificate_fingerprint_sha256
            now = self._now()
            with self._connection() as conn:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    existing = conn.execute(
                        "SELECT * FROM lifecycle_operations WHERE idempotency_key=?",
                        (request.idempotency_key,),
                    ).fetchone()
                    if existing is None:
                        conn.execute("""
                            INSERT INTO lifecycle_operations (
                                idempotency_key,operation_id,request_hash,csr_sha256,operation_hash,
                                authorization_id,outpoint,state,certificate_pem,
                                certificate_fingerprint_sha256,created_at_utc,updated_at_utc
                            ) VALUES (?,?,?,?,?,?,?,'PREPARED',?,?,?,?)
                        """, (
                            request.idempotency_key, request.operation_id, request.request_hash,
                            csr_sha256, request.operation_hash, request.authorization_id, request.outpoint,
                            certificate_pem, certificate_fp, now, now,
                        ))
                    else:
                        if (existing["request_hash"] != request.request_hash
                                or existing["csr_sha256"] != csr_sha256):
                            raise LifecycleError("Concurrent idempotency or CSR conflict")
                        certificate_pem = bytes(existing["certificate_pem"])
                        certificate_fp = existing["certificate_fingerprint_sha256"]
                    conn.commit()
                except Exception:
                    if conn.in_transaction:
                        conn.rollback()
                    raise

        # A crash after this call is recoverable: the same idempotency key
        # returns the same durable UTXO spend and the certificate stays staged.
        finalized = consume_authorization(
            decision=decision,
            request=request,
            backend=self.backend,
            finality_timeout_seconds=finality_timeout_seconds,
        )
        if finalized.evidence.commit_kind not in {
            CommitKind.LOCAL_ACID, CommitKind.NETWORK_CONSENSUS
        }:
            raise LifecycleError("Unsupported authorization commit evidence")
        receipt = {
            "schema": "node-core-os/node-pki-guard-issuance-receipt/v1",
            "operation_id": request.operation_id,
            "idempotency_key": request.idempotency_key,
            "request_hash": request.request_hash,
            "operation_hash": request.operation_hash,
            "authorization_id": request.authorization_id,
            "outpoint": request.outpoint,
            "certificate_fingerprint_sha256": certificate_fp,
            "transaction_id": finalized.submission.transaction_id,
            "commit_kind": finalized.evidence.commit_kind.value,
            "committed_at_utc": finalized.evidence.committed_at_utc,
            "issuer_trust_fingerprint_sha256": self.trusted_issuer_fingerprint_sha256,
            "profile_id": self.profile.profile_id,
            "profile_version": self.profile.profile_version,
            "receipt_key_id": self.receipt_key_id,
        }
        receipt_signature = self._sign_receipt(
            receipt, self.receipt_signing_key_pem, self.receipt_signing_key_password
        )
        receipt_json = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
        now = self._now()
        with self._connection() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                current = conn.execute(
                    "SELECT * FROM lifecycle_operations WHERE idempotency_key=?",
                    (request.idempotency_key,),
                ).fetchone()
                if current is None or current["request_hash"] != request.request_hash:
                    raise LifecycleError("Prepared lifecycle operation disappeared or changed")
                if current["state"] == "COMMITTED":
                    conn.commit()
                    return self._result(current)
                conn.execute("""
                    UPDATE lifecycle_operations
                    SET state='COMMITTED',receipt_json=?,receipt_signature=?,
                        transaction_id=?,commit_kind=?,updated_at_utc=?
                    WHERE idempotency_key=? AND state='PREPARED'
                """, (
                    receipt_json, receipt_signature, finalized.submission.transaction_id,
                    finalized.evidence.commit_kind.value, now, request.idempotency_key,
                ))
                conn.commit()
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise
        row = self._load(request.idempotency_key)
        if row is None:
            raise LifecycleError("Committed lifecycle operation could not be reloaded")
        return self._result(row)

    @staticmethod
    def _result(row: sqlite3.Row) -> LifecycleResult:
        if row["state"] != "COMMITTED" or not row["receipt_json"]:
            raise LifecycleError("Lifecycle operation is not committed")
        return LifecycleResult(
            operation_id=row["operation_id"],
            idempotency_key=row["idempotency_key"],
            state=row["state"],
            certificate_pem=bytes(row["certificate_pem"]),
            certificate_fingerprint_sha256=row["certificate_fingerprint_sha256"],
            receipt=json.loads(row["receipt_json"]),
            receipt_signature=row["receipt_signature"],
            commit_kind=row["commit_kind"],
            transaction_id=row["transaction_id"],
        )

    def recover(self, *, idempotency_key: str) -> dict[str, Any]:
        """Report durable operation state; PREPARED requires retrying issue().

        The caller must resubmit the identical CSR, policy decision and request
        to issue(). The persisted staged certificate is reused; no new CSR or
        UTXO capability may be substituted.
        """
        row = self._load(idempotency_key)
        if row is None:
            raise LifecycleError("Unknown lifecycle idempotency key")
        return {
            "operation_id": row["operation_id"],
            "idempotency_key": row["idempotency_key"],
            "state": row["state"],
            "request_hash": row["request_hash"],
            "certificate_fingerprint_sha256": row["certificate_fingerprint_sha256"],
            "transaction_id": row["transaction_id"],
            "commit_kind": row["commit_kind"],
        }

    @staticmethod
    def verify_receipt_signature(
        receipt: dict[str, Any], signature_b64url: str, issuer_public_key: Any
    ) -> bool:
        import base64
        try:
            signature = base64.urlsafe_b64decode(
                signature_b64url + "=" * (-len(signature_b64url) % 4)
            )
            encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=True, allow_nan=False).encode("utf-8")
            if isinstance(issuer_public_key, ed25519.Ed25519PublicKey):
                issuer_public_key.verify(signature, encoded)
            elif isinstance(issuer_public_key, rsa.RSAPublicKey):
                issuer_public_key.verify(signature, encoded, padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=hashes.SHA256().digest_size), hashes.SHA256())
            elif isinstance(issuer_public_key, ec.EllipticCurvePublicKey):
                issuer_public_key.verify(signature, encoded, ec.ECDSA(hashes.SHA256()))
            else:
                return False
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False
