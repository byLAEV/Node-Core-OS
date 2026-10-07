"""Backup orchestration for encrypted local/file V1 backups."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile

from node_core.backup.encryption import AgeEncryption
from node_core.backup.kubo import KuboBackupSource
from node_core.backup.manifest import create_manifest, serialize_manifest
from node_core.backup.pinata import PinataClient
from node_core.config import NodeConfig


class BackupManager:
    def __init__(self, config: NodeConfig) -> None:
        self.config = config
        self.kubo = KuboBackupSource(config.ipfs_executable, config.ipfs_repo_path)
        self.encryption = AgeEncryption(config.age_executable)
        self.pinata = PinataClient(config.secrets_path / "pinata.jwt")

    def status(self) -> dict[str, object]:
        identity = self.kubo.identity()
        return {
            "age_available": self.encryption.available(),
            "peer_id": identity.peer_id,
            "kubo_version": identity.version,
            "backup_dir": str(self.config.backup_path),
        }

    def inspect(self) -> dict[str, object]:
        identity = self.kubo.identity()
        keys = self.kubo.list_keys()
        manifest = create_manifest(
            kubo_version=identity.version,
            peer_id=identity.peer_id,
            keys=keys,
        )
        return {"manifest": serialize_manifest(manifest).decode("utf-8"), "keys": keys}

    def create_backup(self, passphrase: str, destination: Path | None = None) -> Path:
        if not passphrase:
            raise ValueError("Backup passphrase cannot be empty.")
        if not self.encryption.available():
            raise RuntimeError("age is not available.")

        self.config.ensure_directories()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = Path(destination) if destination is not None else (
            self.config.backup_path / f"NodeCore-Backup-{timestamp}.ncb"
        )
        target = target.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        # Backups are append-only by default. A caller must remove/rename an
        # existing file explicitly rather than silently replacing it.
        if target.exists():
            raise FileExistsError(f"Backup destination already exists: {target}")

        identity = self.kubo.identity()
        keys = self.kubo.list_keys()

        with tempfile.TemporaryDirectory(prefix="node-core-backup-", dir=self.config.backup_path) as work:
            root = Path(work) / "payload"
            keys_dir = root / "keys"
            keys_dir.mkdir(parents=True, mode=0o700)
            identity_dir = root / "identity"
            identity_dir.mkdir(parents=True, mode=0o700)

            self.kubo.export_identity(identity_dir / "kubo-identity.json")
            for name in keys:
                if not name or PurePosixPath(name).name != name or name in {".", ".."}:
                    raise ValueError(f"Unsafe Kubo key name: {name!r}")
                self.kubo.export_key(name, keys_dir / f"{name}.key")

            file_hashes = {}
            for item in sorted(root.rglob("*")):
                if item.is_file():
                    rel = item.relative_to(root).as_posix()
                    file_hashes[rel] = self._sha256(item)

            (root / "manifest.json").write_bytes(
                serialize_manifest(
                    create_manifest(
                        kubo_version=identity.version,
                        peer_id=identity.peer_id,
                        keys=keys,
                        files=file_hashes,
                    )
                )
            )

            archive = Path(work) / "payload.tar"
            with tarfile.open(archive, "w") as tar:
                for item in sorted(root.rglob("*")):
                    tar.add(item, arcname=item.relative_to(root).as_posix())

            encrypted = Path(work) / "backup.ncb"
            self.encryption.encrypt_with_passphrase(archive, encrypted, passphrase)
            self._copy_new_file(encrypted, target)

        if not target.is_file() or target.stat().st_size == 0:
            target.unlink(missing_ok=True)
            raise RuntimeError("Encrypted backup was not created.")

        target.chmod(0o600)
        self._record_history(target, identity.peer_id)
        return target

    def verify_backup(self, path: Path, passphrase: str) -> dict[str, object]:
        path = Path(path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)

        with tempfile.TemporaryDirectory(prefix="node-core-verify-") as work:
            archive = Path(work) / "payload.tar"
            self.encryption.decrypt_with_passphrase(path, archive, passphrase)

            with tarfile.open(archive, "r") as tar:
                members = tar.getmembers()
                names = {member.name for member in members}
                self._validate_tar_names(names)

                if "manifest.json" not in names or "identity/kubo-identity.json" not in names:
                    raise ValueError("Backup is missing required manifest or identity.")

                manifest_member = tar.getmember("manifest.json")
                manifest_data = tar.extractfile(manifest_member)
                if manifest_data is None:
                    raise ValueError("Backup manifest cannot be read.")
                manifest = json.loads(manifest_data.read().decode("utf-8"))

                if manifest.get("format") != "node-core-backup" or manifest.get("version") != 1:
                    raise ValueError("Unsupported Node Core backup format.")

                keys = manifest.get("keys")
                file_hashes = manifest.get("files")
                if not isinstance(keys, list) or not isinstance(file_hashes, dict):
                    raise ValueError("Backup manifest is missing integrity metadata.")

                expected_key_names = {f"keys/{name}.key" for name in keys}
                actual_key_names = {
                    name for name in names if name.startswith("keys/") and name.endswith(".key")
                }
                expected_files = {"identity/kubo-identity.json", *expected_key_names}
                allowed_names = {"manifest.json", *expected_files}
                archive_files = {member.name for member in members if member.isfile()}
                if archive_files != allowed_names:
                    raise ValueError("Backup archive contains unexpected files.")
                if set(file_hashes) != expected_files:
                    raise ValueError("Backup manifest file set does not match the archive.")
                if actual_key_names != expected_key_names:
                    raise ValueError("Backup key set does not match the manifest.")

                identity_member = tar.getmember("identity/kubo-identity.json")
                identity_data = tar.extractfile(identity_member)
                if identity_data is None:
                    raise ValueError("Backup identity cannot be read.")
                identity = json.loads(identity_data.read().decode("utf-8"))
                if not identity.get("PeerID") or not identity.get("PrivKey"):
                    raise ValueError("Backup Kubo identity is incomplete.")
                if manifest.get("peer_id") != identity.get("PeerID"):
                    raise ValueError("Backup peer ID does not match the manifest.")

                for relpath, expected_hash in file_hashes.items():
                    member = tar.getmember(relpath)
                    data = tar.extractfile(member)
                    if data is None or not member.isfile():
                        raise ValueError(f"Backup member is not a regular file: {relpath}")
                    actual_hash = hashlib.sha256(data.read()).hexdigest()
                    if actual_hash != expected_hash:
                        raise ValueError(f"Backup integrity check failed: {relpath}")

        return {
            "valid": True,
            "manifest": manifest,
            "key_count": len(actual_key_names),
            "identity_present": True,
            "sha256": self._sha256(path),
        }

    def upload_to_pinata(self, path: Path) -> dict[str, object]:
        path = Path(path)
        if path.suffix.lower() != ".ncb":
            raise ValueError("Only encrypted .ncb backups may be uploaded to Pinata.")
        result = self.pinata.upload_file(path)
        self._append_history({
            "created_at": datetime.now(timezone.utc).isoformat(),
            "path": str(path),
            "cid": result["cid"],
            "provider": "pinata",
            "encrypted": True,
        })
        return result

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _copy_new_file(source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as src, target.open("xb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
            dst.flush()

    @staticmethod
    def _validate_tar_names(names: set[str]) -> None:
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or name.startswith("/"):
                raise ValueError(f"Unsafe archive member: {name}")

    def _append_history(self, record: dict[str, object]) -> None:
        history = []
        if self.config.backup_history_path.exists():
            history = json.loads(self.config.backup_history_path.read_text(encoding="utf-8"))
            if not isinstance(history, list):
                raise ValueError("Backup history is not a JSON list.")
        history.append(record)
        self.config.backup_path.mkdir(parents=True, exist_ok=True)
        temp = self.config.backup_history_path.with_name("history.json.tmp")
        temp.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
        temp.chmod(0o600)
        temp.replace(self.config.backup_history_path)

    def _record_history(self, path: Path, peer_id: str | None) -> None:
        self._append_history({
            "created_at": datetime.now(timezone.utc).isoformat(),
            "path": str(path),
            "sha256": self._sha256(path),
            "encrypted": True,
            "peer_id": peer_id,
        })
