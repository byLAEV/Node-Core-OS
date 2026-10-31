"""GitHub-owned identity repositories and encrypted personal-record intake.

Public repositories store ciphertext only. Plaintext records are kept in the
owning node's private local data directory. This module does not claim
personhood verification, document authenticity, or network consensus.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


POOL_SCHEMA = "node-core-os/github-identity-pool/v1"
ENVELOPE_SCHEMA = "node-core-os/personal-identity-envelope/v1"
RECORD_SCHEMA = "node-core-os/personal-identity-record/v1"
MAX_ENVELOPE_BYTES = 1_000_000
MAX_RECORD_FIELD_LENGTH = 4096
GITHUB_API = "https://api.github.com"
_LOGIN = re.compile(r"^(?!-)[A-Za-z0-9-]{1,39}(?<!-)$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


class GitHubIdentityPoolError(RuntimeError):
    """Raised when the GitHub identity pool or encrypted intake is invalid."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    if not isinstance(value, str) or len(value) > MAX_ENVELOPE_BYTES * 2:
        raise GitHubIdentityPoolError("Encrypted field is missing or too large.")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise GitHubIdentityPoolError("Encrypted field is not valid base64.") from exc


def _safe_login(login: str) -> str:
    if not isinstance(login, str) or not _LOGIN.fullmatch(login):
        raise GitHubIdentityPoolError("GitHub login must be 1–39 letters, digits or hyphens and cannot start or end with a hyphen.")
    return login.lower()


def _safe_repository(login: str, repository: str) -> str:
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise GitHubIdentityPoolError("Repository must use owner/repository format.")
    owner, name = repository.split("/", 1)
    if owner.lower() != login.lower() or not _REPOSITORY.fullmatch(name) or name in {".", ".."}:
        raise GitHubIdentityPoolError("The repository owner must match the GitHub login and the repository name must be valid.")
    return f"{owner}/{name}"


def _safe_pages_url(login: str, repository: str, pages_url: str | None) -> str:
    name = repository.split("/", 1)[1]
    expected = f"https://{login}.github.io/{name}/"
    value = (pages_url or expected).strip()
    if value.rstrip("/") != expected.rstrip("/"):
        raise GitHubIdentityPoolError(f"GitHub Pages URL must match this account's repository: {expected}")
    return expected


def _atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}-", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        try:
            os.chmod(path, mode)
        except OSError:
            pass
    finally:
        if temporary.exists():
            temporary.unlink()


class GitHubIdentityPool:
    """Manage this node's GitHub client, admitted GitHub nodes and encrypted records."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir).expanduser()
        self.root = self.data_dir / "identity" / "github-pool"
        self.private_dir = self.root / "private"
        self.records_dir = self.root / "records"
        self.pool_path = self.root / "pool.json"
        self.private_key_path = self.private_dir / "record-encryption-private.pem"
        self.public_key_path = self.root / "record-encryption-public.json"
        self.shared_dir = self.data_dir / "storage" / "shared" / "github-identity-pool"
        self.shared_envelopes_dir = self.shared_dir / "envelopes"
        self.shared_index_path = self.shared_dir / "index.json"

    def initialize(self, admin_node_id: str) -> dict[str, Any]:
        if not isinstance(admin_node_id, str) or not admin_node_id.strip():
            raise GitHubIdentityPoolError("The administrator node ID is required.")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.root, 0o700)
            os.chmod(self.private_dir, 0o700)
        except OSError:
            pass

        if self.private_key_path.exists():
            private_key = self._load_private_key()
        else:
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
            pem = private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
            _atomic_write(self.private_key_path, pem, 0o600)

        public_jwk = self._public_jwk(private_key)
        key_id = hashlib.sha256(_canonical_json(public_jwk)).hexdigest()
        public_document = {
            "schema": "node-core-os/record-encryption-key/v1",
            "key_id": key_id,
            "algorithm": "RSA-OAEP-256 + AES-256-GCM",
            "public_jwk": public_jwk,
        }
        _atomic_write(self.public_key_path, _canonical_json(public_document) + b"\n", 0o644)

        if self.pool_path.exists():
            state = self._read_pool()
            if state["admin_node_id"] != admin_node_id:
                raise GitHubIdentityPoolError(
                    "This pool belongs to a different administrator node. Do not silently transfer its ownership."
                )
        else:
            state = {
                "schema": POOL_SCHEMA,
                "pool_id": str(uuid.uuid4()),
                "admin_node_id": admin_node_id,
                "created_at_utc": _now(),
                "local_client": None,
                "nodes": [],
            }
            self._write_pool(state)
        return {
            "pool_id": state["pool_id"],
            "admin_node_id": state["admin_node_id"],
            "node_count": len(state["nodes"]),
            "encryption_key_id": key_id,
            "private_key_path": str(self.private_key_path),
        }

    def public_encryption_key(self) -> dict[str, Any]:
        self._require_initialized()
        try:
            document = json.loads(self.public_key_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GitHubIdentityPoolError("Public encryption-key file is missing or invalid.") from exc
        return document

    def configure_local_client(
        self,
        github_login: str,
        repository: str,
        pages_url: str | None = None,
        default_branch: str = "main",
    ) -> dict[str, Any]:
        self._require_initialized()
        login = _safe_login(github_login)
        repo = _safe_repository(login, repository)
        page = _safe_pages_url(login, repo, pages_url)
        if not isinstance(default_branch, str) or not re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", default_branch):
            raise GitHubIdentityPoolError("Default branch contains unsupported characters.")
        state = self._read_pool()
        state["local_client"] = {
            "github_login": login,
            "repository": repo,
            "pages_url": page,
            "default_branch": default_branch,
            "configured_at_utc": _now(),
        }
        self._write_pool(state)
        return dict(state["local_client"])

    def local_client(self) -> dict[str, Any] | None:
        self._require_initialized()
        value = self._read_pool().get("local_client")
        return dict(value) if isinstance(value, dict) else None

    def add_node(
        self,
        github_login: str,
        repository: str,
        pages_url: str | None = None,
        *,
        node_id: str | None = None,
        repository_id: int | None = None,
    ) -> dict[str, Any]:
        """Add a GitHub-owned Node Core client as pending; registration is not trust."""
        self._require_initialized()
        login = _safe_login(github_login)
        repo = _safe_repository(login, repository)
        page = _safe_pages_url(login, repo, pages_url)
        if node_id is not None and (
            not isinstance(node_id, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", node_id)
        ):
            raise GitHubIdentityPoolError("Node ID must use sha256:<64 lowercase hexadecimal characters>.")
        if repository_id is not None and (
            not isinstance(repository_id, int) or isinstance(repository_id, bool) or repository_id <= 0
        ):
            raise GitHubIdentityPoolError("GitHub repository ID must be a positive integer.")
        state = self._read_pool()
        for existing in state["nodes"]:
            if existing["github_login"].lower() == login:
                if existing["repository"] == repo and existing["status"] != "revoked":
                    return dict(existing)
                raise GitHubIdentityPoolError("This GitHub account is already registered. Reconcile or revoke the existing entry first.")
        record = {
            "member_id": str(uuid.uuid4()),
            "github_login": login,
            "repository": repo,
            "repository_id": repository_id,
            "pages_url": page,
            "node_id": node_id,
            "status": "pending_admin_verification",
            "verification_status": "not_verified",
            "added_at_utc": _now(),
            "revoked_at_utc": None,
            "last_seen_at_utc": None,
        }
        state["nodes"].append(record)
        self._write_pool(state)
        return dict(record)

    def list_nodes(self) -> list[dict[str, Any]]:
        self._require_initialized()
        return [dict(item) for item in self._read_pool()["nodes"]]

    def revoke_node(self, member_id: str) -> dict[str, Any]:
        self._require_initialized()
        state = self._read_pool()
        for item in state["nodes"]:
            if item["member_id"] == member_id:
                item["status"] = "revoked"
                item["revoked_at_utc"] = item["revoked_at_utc"] or _now()
                self._write_pool(state)
                return dict(item)
        raise GitHubIdentityPoolError("GitHub node was not found in this pool.")

    def export_client_package(self, target_dir: Path) -> Path:
        """Export a minimal static Pages client; never copy the full installer repository."""
        self._require_initialized()
        client = self.local_client()
        if client is None:
            raise GitHubIdentityPoolError("Configure this node's own GitHub account and repository first.")
        source = Path(__file__).resolve().parents[2] / "client-template"
        if not source.is_dir():
            raise GitHubIdentityPoolError(f"Client template directory is missing: {source}")
        target = Path(target_dir).expanduser()
        if target.exists() and any(target.iterdir()):
            raise GitHubIdentityPoolError(f"Refusing to overwrite a non-empty export directory: {target}")
        if target.exists():
            target.rmdir()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
        pool = self._read_pool()
        key = self.public_encryption_key()
        config = {
            "schema": "node-core-os/github-pages-client/v1",
            "pool_id": pool["pool_id"],
            "owner_login": client["github_login"],
            "repository": client["repository"],
            "default_branch": client["default_branch"],
            "pages_url": client["pages_url"],
            "node_id": pool["admin_node_id"],
            "record_encryption": key,
            "records_path": "records",
            "client_version": "1.0.0",
        }
        _atomic_write(
            target / "node-core-client.json",
            json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
            0o644,
        )
        return target

    def sync_local_repository(self, token: str | None = None, kubo: Any | None = None) -> dict[str, Any]:
        """Read this node owner's GitHub Pages repository and ingest encrypted records.

        A supplied token is checked with GET /user and must belong to the configured
        repository owner. Without a token only public repositories can be read.
        """
        self._require_initialized()
        client = self.local_client()
        if client is None:
            raise GitHubIdentityPoolError("Configure this node's GitHub repository before synchronizing.")
        token = token or self._github_cli_token()
        if token:
            user = self._github_api("/user", token)
            if not isinstance(user, dict) or str(user.get("login", "")).lower() != client["github_login"]:
                raise GitHubIdentityPoolError("GitHub credential does not belong to the configured repository owner.")
        repository = self._github_api(f"/repos/{client['repository']}", token)
        if not isinstance(repository, dict):
            raise GitHubIdentityPoolError("GitHub repository metadata is unavailable.")
        owner = repository.get("owner") or {}
        if str(owner.get("login", "")).lower() != client["github_login"]:
            raise GitHubIdentityPoolError("GitHub repository owner does not match the configured account.")
        saved_repository_id = repository.get("id")
        saved_branch = repository.get("default_branch") or client["default_branch"]
        directory = self._github_api(
            f"/repos/{client['repository']}/contents/records?ref={quote(saved_branch, safe='')}",
            token,
            allow_not_found=True,
        )
        if directory is None:
            files = []
        elif isinstance(directory, list):
            files = directory
        else:
            raise GitHubIdentityPoolError("GitHub records directory returned an unexpected response.")

        imported = 0
        skipped = 0
        ipfs_cids: list[str] = []
        for item in files:
            if not isinstance(item, dict) or item.get("type") != "file":
                continue
            name = item.get("name")
            path = item.get("path")
            if (
                not isinstance(name, str)
                or not re.fullmatch(r"[0-9a-fA-F-]{36}\.json", name)
                or path != f"records/{name}"
            ):
                skipped += 1
                continue
            size = item.get("size", 0)
            if not isinstance(size, int) or size < 1 or size > MAX_ENVELOPE_BYTES:
                skipped += 1
                continue
            content = self._github_api(
                f"/repos/{client['repository']}/contents/{quote(path, safe='/')}?ref={quote(saved_branch, safe='')}",
                token,
            )
            if not isinstance(content, dict) or content.get("encoding") != "base64":
                skipped += 1
                continue
            raw = _b64decode(content.get("content", ""))
            if len(raw) > MAX_ENVELOPE_BYTES:
                skipped += 1
                continue
            try:
                envelope = json.loads(raw.decode("utf-8"))
                result = self.ingest_envelope(envelope, kubo=kubo, owner_login=client["github_login"])
                if result.get("created"):
                    imported += 1
                if result.get("ipfs_cid"):
                    ipfs_cids.append(result["ipfs_cid"])
            except (UnicodeError, json.JSONDecodeError, GitHubIdentityPoolError, ValueError):
                skipped += 1

        state = self._read_pool()
        state["local_client"]["repository_id"] = saved_repository_id
        state["local_client"]["default_branch"] = saved_branch
        state["local_client"]["last_sync_at_utc"] = _now()
        state["local_client"]["last_sync_imported"] = imported
        self._write_pool(state)
        return {
            "repository": client["repository"],
            "repository_id": saved_repository_id,
            "files_seen": len(files),
            "records_imported": imported,
            "files_skipped": skipped,
            "ipfs_cids": ipfs_cids,
            "sync_at_utc": state["local_client"]["last_sync_at_utc"],
        }

    def encrypt_record(self, fields: dict[str, str], *, consent_given: bool) -> dict[str, Any]:
        """Create a browser-compatible RSA-OAEP/AES-GCM envelope for a consented record."""
        self._require_initialized()
        record_id = str(uuid.uuid4())
        record = {
            "schema": RECORD_SCHEMA,
            "record_id": record_id,
            "created_at_utc": _now(),
            "consent_given": consent_given,
            "fields": fields,
        }
        self._validate_plain_record(record, record_id)
        if consent_given is not True:
            raise GitHubIdentityPoolError("Explicit consent is required.")
        public_document = self.public_encryption_key()
        public_numbers = self._load_private_key().public_key().public_numbers()
        public_key = rsa.RSAPublicNumbers(public_numbers.e, public_numbers.n).public_key()
        aes_key = AESGCM.generate_key(bit_length=256)
        nonce = os.urandom(12)
        associated_data = f"{ENVELOPE_SCHEMA}|{record_id}|{public_document['key_id']}".encode()
        ciphertext = AESGCM(aes_key).encrypt(nonce, _canonical_json(record), associated_data)
        wrapped_key = public_key.encrypt(
            aes_key,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        )
        return {
            "schema": ENVELOPE_SCHEMA,
            "record_id": record_id,
            "created_at_utc": record["created_at_utc"],
            "encryption_key_id": public_document["key_id"],
            "algorithm": "RSA-OAEP-256+A256GCM",
            "wrapped_key": base64.b64encode(wrapped_key).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }

    def ingest_envelope(
        self,
        envelope: dict[str, Any],
        *,
        kubo: Any | None = None,
        owner_login: str | None = None,
    ) -> dict[str, Any]:
        """Decrypt one Pages record locally and place only ciphertext in shared storage."""
        self._require_initialized()
        if not isinstance(envelope, dict) or envelope.get("schema") != ENVELOPE_SCHEMA:
            raise GitHubIdentityPoolError("Unsupported encrypted identity-record envelope.")
        record_id = envelope.get("record_id")
        try:
            parsed_id = str(uuid.UUID(record_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise GitHubIdentityPoolError("Envelope record ID must be a UUID.") from exc
        if parsed_id != record_id.lower():
            raise GitHubIdentityPoolError("Envelope record ID must use canonical UUID format.")
        if envelope.get("encryption_key_id") != self.public_encryption_key()["key_id"]:
            raise GitHubIdentityPoolError("Encrypted record targets a different node encryption key.")
        created_at = envelope.get("created_at_utc")
        if not isinstance(created_at, str) or len(created_at) > 64:
            raise GitHubIdentityPoolError("Envelope creation timestamp is invalid.")
        raw_envelope = _canonical_json(envelope)
        if len(raw_envelope) > MAX_ENVELOPE_BYTES:
            raise GitHubIdentityPoolError("Encrypted record exceeds the size limit.")

        private_key = self._load_private_key()
        try:
            aes_key = private_key.decrypt(
                _b64decode(envelope.get("wrapped_key", "")),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            nonce = _b64decode(envelope.get("nonce", ""))
            ciphertext = _b64decode(envelope.get("ciphertext", ""))
            associated_data = f"{ENVELOPE_SCHEMA}|{record_id}|{envelope['encryption_key_id']}".encode()
            plaintext = AESGCM(aes_key).decrypt(nonce, ciphertext, associated_data)
            record = json.loads(plaintext.decode("utf-8"))
        except GitHubIdentityPoolError:
            raise
        except Exception as exc:
            raise GitHubIdentityPoolError("Encrypted identity record failed authenticated decryption.") from exc

        self._validate_plain_record(record, record_id)
        private_path = self.records_dir / f"{record_id}.json"
        if private_path.exists():
            try:
                previous = json.loads(private_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise GitHubIdentityPoolError("Existing private record is unreadable; refusing overwrite.") from exc
            if previous != record:
                raise GitHubIdentityPoolError("Record ID already exists with different personal data.")
            created = False
        else:
            _atomic_write(private_path, json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8") + b"\n", 0o600)
            created = True

        self.shared_envelopes_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        envelope_path = self.shared_envelopes_dir / f"{record_id}.json"
        if envelope_path.exists():
            existing = envelope_path.read_bytes()
            if existing != raw_envelope + b"\n":
                raise GitHubIdentityPoolError("A different encrypted envelope already exists for this record ID.")
        else:
            _atomic_write(envelope_path, raw_envelope + b"\n", 0o600)

        index = self._read_shared_index()
        digest = hashlib.sha256(raw_envelope).hexdigest()
        entry = {
            "record_id": record_id,
            "ciphertext_sha256": digest,
            "owner_login": owner_login or "",
            "created_at_utc": created_at,
            "encrypted_path": str(envelope_path),
            "ipfs_cid": None,
        }
        existing_entry = next((item for item in index["records"] if item["record_id"] == record_id), None)
        if existing_entry and existing_entry["ciphertext_sha256"] != digest:
            raise GitHubIdentityPoolError("Shared replication index contains a conflicting record ID.")
        if not existing_entry:
            index["records"].append(entry)

        ipfs_cid = None
        if kubo is not None:
            try:
                status = kubo.status()
                if status.running:
                    added = kubo.add_file(envelope_path, pin=True)
                    ipfs_cid = added.cid
                    for item in index["records"]:
                        if item["record_id"] == record_id:
                            item["ipfs_cid"] = ipfs_cid
                            break
            except Exception:
                # Local encrypted storage succeeds even when Kubo is offline.
                ipfs_cid = None
        index["updated_at_utc"] = _now()
        self._write_shared_index(index)
        return {
            "record_id": record_id,
            "created": created,
            "private_record_path": str(private_path),
            "encrypted_replica_path": str(envelope_path),
            "ciphertext_sha256": digest,
            "ipfs_cid": ipfs_cid,
        }

    def _validate_plain_record(self, record: Any, record_id: str) -> None:
        if not isinstance(record, dict) or record.get("schema") != RECORD_SCHEMA:
            raise GitHubIdentityPoolError("Decrypted payload does not use the personal identity record schema.")
        if record.get("record_id") != record_id:
            raise GitHubIdentityPoolError("Decrypted payload record ID does not match its envelope.")
        if record.get("consent_given") is not True:
            raise GitHubIdentityPoolError("Personal identity record lacks an explicit consent declaration.")
        fields = record.get("fields")
        if not isinstance(fields, dict) or not fields or len(fields) > 32:
            raise GitHubIdentityPoolError("Personal identity fields must be a non-empty object with at most 32 entries.")
        for name, value in fields.items():
            if (
                not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name)
                or not isinstance(value, str) or len(value) > MAX_RECORD_FIELD_LENGTH
            ):
                raise GitHubIdentityPoolError("Personal identity record contains an invalid field.")

    def _read_pool(self) -> dict[str, Any]:
        try:
            value = json.loads(self.pool_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GitHubIdentityPoolError("GitHub identity pool is unreadable or invalid JSON.") from exc
        if (
            not isinstance(value, dict) or value.get("schema") != POOL_SCHEMA
            or not isinstance(value.get("nodes"), list)
            or not isinstance(value.get("pool_id"), str)
            or not isinstance(value.get("admin_node_id"), str)
        ):
            raise GitHubIdentityPoolError("GitHub identity pool schema is invalid.")
        return value

    def _write_pool(self, state: dict[str, Any]) -> None:
        _atomic_write(self.pool_path, json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8") + b"\n", 0o600)

    def _read_shared_index(self) -> dict[str, Any]:
        if not self.shared_index_path.exists():
            return {"schema": "node-core-os/github-identity-replication-index/v1", "records": [], "updated_at_utc": None}
        try:
            value = json.loads(self.shared_index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GitHubIdentityPoolError("Encrypted replication index is unreadable.") from exc
        if not isinstance(value, dict) or not isinstance(value.get("records"), list):
            raise GitHubIdentityPoolError("Encrypted replication index schema is invalid.")
        return value

    def _write_shared_index(self, index: dict[str, Any]) -> None:
        _atomic_write(
            self.shared_index_path,
            json.dumps(index, ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
            0o600,
        )

    def _require_initialized(self) -> None:
        if not self.pool_path.is_file() or not self.private_key_path.is_file() or not self.public_key_path.is_file():
            raise GitHubIdentityPoolError("Initialize the GitHub Identity Pool before using this operation.")

    def _load_private_key(self):
        try:
            key = serialization.load_pem_private_key(self.private_key_path.read_bytes(), password=None)
        except (OSError, ValueError, TypeError) as exc:
            raise GitHubIdentityPoolError("Local record-encryption private key is unreadable.") from exc
        if not isinstance(key, rsa.RSAPrivateKey):
            raise GitHubIdentityPoolError("Local record-encryption key is not RSA.")
        return key

    @staticmethod
    def _public_jwk(private_key: rsa.RSAPrivateKey) -> dict[str, Any]:
        numbers = private_key.public_key().public_numbers()
        return {
            "kty": "RSA",
            "alg": "RSA-OAEP-256",
            "use": "enc",
            "key_ops": ["encrypt"],
            "ext": True,
            "n": _b64url(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
            "e": _b64url(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
        }

    @staticmethod
    def _github_cli_token() -> str | None:
        if os.environ.get("NODE_CORE_GITHUB_TOKEN"):
            return os.environ["NODE_CORE_GITHUB_TOKEN"]
        executable = shutil.which("gh")
        if not executable:
            return None
        try:
            result = subprocess.run(
                [executable, "auth", "token"],
                check=True, capture_output=True, text=True, timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        token = result.stdout.strip()
        return token or None

    @staticmethod
    def _github_api(path: str, token: str | None = None, *, allow_not_found: bool = False) -> Any:
        url = path if path.startswith("https://") else f"{GITHUB_API}{path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Node-Core-OS-GitHub-Identity-Pool",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read(MAX_ENVELOPE_BYTES + 1)
        except HTTPError as exc:
            if exc.code == 404 and allow_not_found:
                return None
            if exc.code == 404:
                raise GitHubIdentityPoolError("GitHub resource not found or not accessible to this credential.") from exc
            raise GitHubIdentityPoolError(f"GitHub API returned HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise GitHubIdentityPoolError(f"GitHub API request failed: {exc.__class__.__name__}.") from exc
        if len(raw) > MAX_ENVELOPE_BYTES:
            raise GitHubIdentityPoolError("GitHub API response exceeded the configured size limit.")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise GitHubIdentityPoolError("GitHub API returned invalid JSON.") from exc
