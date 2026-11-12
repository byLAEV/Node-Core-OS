"""Standalone SQLite implementation of the NODE-PKI-GUARD backend contract.

This backend provides single-host ACID semantics only. It is not a distributed
ledger and its local commit evidence must never be presented as network finality.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from node_core.security.node_pki_guard_backend import (
    AuthorizationUTXO,
    BackendContractError,
    CommitEvidence,
    CommitKind,
    IdempotencyConflict,
    SpendRequest,
    SpendState,
    SpendSubmission,
    UTXOAuthorizationBackend,
    UTXOStatus,
)


class StandaloneSQLiteBackend(UTXOAuthorizationBackend):
    """Durable single-host UTXO store using SQLite WAL and immediate writes."""

    SCHEMA_VERSION = 2

    def __init__(self, db_path: str | Path = "node_pki_guard.db", timeout: float = 10.0):
        self.db_path = str(Path(db_path).expanduser())
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.timeout = float(timeout)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.timeout,
            isolation_level=None,
        )
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(f"PRAGMA busy_timeout = {int(self.timeout * 1000)}")
            yield conn
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._connection() as conn:
            mode = conn.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            if str(mode).lower() != "wal":
                raise BackendContractError("SQLite could not enable WAL mode")
            conn.execute("PRAGMA synchronous = FULL")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS authorization_utxos (
                    outpoint TEXT PRIMARY KEY,
                    authorization_id TEXT NOT NULL UNIQUE,
                    binding_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    owner_key_id TEXT NOT NULL,
                    operation_hash TEXT NOT NULL,
                    policy_id TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    authorization_payload_hash TEXT,
                    status TEXT NOT NULL CHECK(status IN ('UNSPENT', 'SPENT')),
                    registered_at_utc TEXT NOT NULL,
                    spent_at_utc TEXT,
                    spent_operation_id TEXT
                );

                CREATE TABLE IF NOT EXISTS spend_records (
                    transaction_id TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    operation_hash TEXT NOT NULL,
                    authorization_id TEXT NOT NULL,
                    outpoint TEXT NOT NULL UNIQUE,
                    binding_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    owner_key_id TEXT NOT NULL,
                    policy_id TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state = 'LOCAL_COMMITTED'),
                    fee_charged INTEGER NOT NULL CHECK(fee_charged = 0),
                    receipt_json TEXT NOT NULL,
                    receipt_hash TEXT NOT NULL,
                    committed_at_utc TEXT NOT NULL,
                    UNIQUE(operation_id, idempotency_key),
                    FOREIGN KEY(outpoint) REFERENCES authorization_utxos(outpoint)
                );

                CREATE INDEX IF NOT EXISTS idx_spend_operation
                    ON spend_records(operation_id);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_spend_idempotency_global
                    ON spend_records(idempotency_key);
                INSERT OR IGNORE INTO schema_metadata(key, value)
                    VALUES ('schema_version', '1');
            """)
            columns = {
                row["name"] for row in conn.execute(
                    "PRAGMA table_info(authorization_utxos)"
                ).fetchall()
            }
            if "authorization_payload_hash" not in columns:
                conn.execute(
                    "ALTER TABLE authorization_utxos ADD COLUMN authorization_payload_hash TEXT"
                )
            version = conn.execute(
                "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
            ).fetchone()
            if version is None:
                raise BackendContractError("SQLite backend schema metadata is missing")
            current_version = int(version["value"])
            if current_version > self.SCHEMA_VERSION or current_version < 1:
                raise BackendContractError("Unsupported SQLite backend schema version")
            conn.execute(
                "UPDATE schema_metadata SET value = ? WHERE key = 'schema_version'",
                (str(self.SCHEMA_VERSION),),
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")

    @staticmethod
    def _transaction_id(request: SpendRequest) -> str:
        material = (
            "NODE-PKI-GUARD-LOCAL-TX-v1\\0"
            + request.operation_id + "\\0"
            + request.idempotency_key + "\\0"
            + request.request_hash
        ).encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    @staticmethod
    def _submission(row: sqlite3.Row) -> SpendSubmission:
        return SpendSubmission(
            transaction_id=row["transaction_id"],
            request_hash=row["request_hash"],
            outpoint=row["outpoint"],
            operation_id=row["operation_id"],
            idempotency_key=row["idempotency_key"],
            operation_hash=row["operation_hash"],
            authorization_id=row["authorization_id"],
            state=SpendState.LOCAL_COMMITTED,
            fee_charged=row["fee_charged"],
        )

    def register_authorization(self, authorization: AuthorizationUTXO) -> None:
        now = self._now()
        with self._connection() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                existing = conn.execute(
                    "SELECT * FROM authorization_utxos WHERE outpoint = ?",
                    (authorization.outpoint,),
                ).fetchone()
                values = (
                    authorization.authorization_id, authorization.binding_id,
                    authorization.node_id, authorization.owner_key_id,
                    authorization.operation_hash, authorization.policy_id,
                    authorization.policy_version,
                    authorization.authorization_payload_hash,
                )
                if existing is not None:
                    stored = tuple(existing[key] for key in (
                        "authorization_id", "binding_id", "node_id", "owner_key_id",
                        "operation_hash", "policy_id", "policy_version",
                        "authorization_payload_hash",
                    ))
                    if stored != values:
                        raise BackendContractError(
                            "Outpoint already exists with different authorization content"
                        )
                    conn.commit()
                    return
                conn.execute("""
                    INSERT INTO authorization_utxos (
                        outpoint, authorization_id, binding_id, node_id, owner_key_id,
                        operation_hash, policy_id, policy_version, status, registered_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'UNSPENT', ?)
                """, (authorization.outpoint, *values, now))
                conn.commit()
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise

    def get_utxo_status(self, outpoint: str) -> UTXOStatus:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT status FROM authorization_utxos WHERE outpoint = ?",
                (outpoint,),
            ).fetchone()
        if row is None:
            return UTXOStatus.NOT_FOUND
        return UTXOStatus(row["status"])

    def get_authorization(self, outpoint: str) -> AuthorizationUTXO | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM authorization_utxos WHERE outpoint = ?", (outpoint,)).fetchone()
        if row is None:
            return None
        return AuthorizationUTXO(
            outpoint=row["outpoint"], authorization_id=row["authorization_id"],
            binding_id=row["binding_id"], node_id=row["node_id"],
            owner_key_id=row["owner_key_id"], operation_hash=row["operation_hash"],
            policy_id=row["policy_id"], policy_version=row["policy_version"],
            authorization_payload_hash=row["authorization_payload_hash"],
        )

    def get_idempotent_result(self, idempotency_key: str) -> SpendSubmission | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM spend_records WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        return None if row is None else self._submission(row)

    def submit_spend_atomic(self, request: SpendRequest) -> SpendSubmission:
        if request.fee_amount != 0 or request.fee_asset != "NONE":
            raise BackendContractError("Standalone backend does not accept network fees")
        transaction_id = self._transaction_id(request)
        now = self._now()
        receipt = {
            "schema": "node-core-os/node-pki-guard-local-receipt/v1",
            "transaction_id": transaction_id,
            "operation_id": request.operation_id,
            "idempotency_key": request.idempotency_key,
            "request_hash": request.request_hash,
            "operation_hash": request.operation_hash,
            "authorization_id": request.authorization_id,
            "outpoint": request.outpoint,
            "binding_id": request.binding_id,
            "node_id": request.node_id,
            "policy_id": request.policy_id,
            "policy_version": request.policy_version,
            "commit_kind": CommitKind.LOCAL_ACID.value,
            "committed_at_utc": now,
        }
        receipt_json = json.dumps(
            receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        receipt_hash = hashlib.sha256(receipt_json.encode("utf-8")).hexdigest()

        with self._connection() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                previous = conn.execute("""
                    SELECT * FROM spend_records
                    WHERE idempotency_key = ?
                """, (request.idempotency_key,)).fetchone()
                if previous is not None:
                    if previous["request_hash"] != request.request_hash or previous["operation_id"] != request.operation_id:
                        raise IdempotencyConflict(
                            "Idempotency key was reused with different request content"
                        )
                    conn.commit()
                    return self._submission(previous)

                authorization = conn.execute("""
                    SELECT * FROM authorization_utxos WHERE outpoint = ?
                """, (request.outpoint,)).fetchone()
                if authorization is None:
                    raise BackendContractError("Authorization outpoint was not found")
                expected = {
                    "authorization_id": request.authorization_id,
                    "binding_id": request.binding_id,
                    "node_id": request.node_id,
                    "owner_key_id": request.owner_key_id,
                    "operation_hash": request.operation_hash,
                    "policy_id": request.policy_id,
                    "policy_version": request.policy_version,
                }
                for field, value in expected.items():
                    if authorization[field] != value:
                        raise BackendContractError(
                            "Spend request does not match registered authorization: " + field
                        )
                if authorization["status"] != UTXOStatus.UNSPENT.value:
                    raise BackendContractError("Authorization outpoint is already spent")

                updated = conn.execute("""
                    UPDATE authorization_utxos
                    SET status = 'SPENT', spent_at_utc = ?, spent_operation_id = ?
                    WHERE outpoint = ? AND status = 'UNSPENT'
                """, (now, request.operation_id, request.outpoint))
                if updated.rowcount != 1:
                    raise BackendContractError("Atomic outpoint transition did not update exactly one row")

                conn.execute("""
                    INSERT INTO spend_records (
                        transaction_id, operation_id, idempotency_key, request_hash,
                        operation_hash, authorization_id, outpoint, binding_id, node_id,
                        owner_key_id, policy_id, policy_version, state, fee_charged,
                        receipt_json, receipt_hash, committed_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'LOCAL_COMMITTED',
                              0, ?, ?, ?)
                """, (
                    transaction_id, request.operation_id, request.idempotency_key,
                    request.request_hash, request.operation_hash, request.authorization_id,
                    request.outpoint, request.binding_id, request.node_id, request.owner_key_id,
                    request.policy_id, request.policy_version, receipt_json, receipt_hash, now,
                ))
                conn.commit()
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise

        return SpendSubmission(
            transaction_id=transaction_id,
            request_hash=request.request_hash,
            outpoint=request.outpoint,
            operation_id=request.operation_id,
            idempotency_key=request.idempotency_key,
            operation_hash=request.operation_hash,
            authorization_id=request.authorization_id,
            state=SpendState.LOCAL_COMMITTED,
            fee_charged=0,
        )

    def wait_for_commit(self, transaction_id: str, timeout_seconds: float) -> CommitEvidence:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM spend_records WHERE transaction_id = ?",
                (transaction_id,),
            ).fetchone()
        if row is None:
            raise BackendContractError("Local transaction has not been committed")
        return CommitEvidence(
            transaction_id=transaction_id,
            commit_kind=CommitKind.LOCAL_ACID,
            backend_id="standalone-sqlite",
            committed_at_utc=row["committed_at_utc"],
            sequence=0,
            evidence_hash=row["receipt_hash"],
            external_proof={"receipt": json.loads(row["receipt_json"])},
        )

    def verify_commit_evidence(
        self, evidence: CommitEvidence, transaction_id: str
    ) -> bool:
        if evidence.transaction_id != transaction_id or evidence.commit_kind is not CommitKind.LOCAL_ACID:
            return False
        try:
            receipt = evidence.external_proof["receipt"]
            encoded = json.dumps(
                receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
            digest = hashlib.sha256(encoded).hexdigest()
        except (KeyError, TypeError, ValueError):
            return False
        if digest != evidence.evidence_hash:
            return False
        with self._connection() as conn:
            row = conn.execute("""
                SELECT receipt_hash, committed_at_utc
                FROM spend_records WHERE transaction_id = ?
            """, (transaction_id,)).fetchone()
        return (
            row is not None
            and row["receipt_hash"] == evidence.evidence_hash
            and row["committed_at_utc"] == evidence.committed_at_utc
            and receipt.get("transaction_id") == transaction_id
            and receipt.get("commit_kind") == CommitKind.LOCAL_ACID.value
        )

    def get_receipt(self, transaction_id: str) -> dict | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT receipt_json FROM spend_records WHERE transaction_id = ?",
                (transaction_id,),
            ).fetchone()
        return None if row is None else json.loads(row["receipt_json"])
