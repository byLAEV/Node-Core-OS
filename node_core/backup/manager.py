"""Backup orchestration for encrypted local/file V1 backups."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
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
        manifest = create_manifest(kubo_version=identity.version, peer_id=identity.peer_id, keys=keys)
        return {"manifest": serialize_manifest(manifest).decode("utf-8"), "keys": keys}

    def create_backup(self, passphrase: str, destination: Path | None = None) -> Path:
        if not passphrase:
            raise ValueError("Backup passphrase cannot be empty.")
        if not self.encryption.available():
            raise RuntimeError("age is not available.")
        self.config.ensure_directories()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = destination or (self.config.backup_path / f"NodeCore-Backup-{timestamp}.ncb")
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.chmod(0o600) if target.exists() else None

        with tempfile.TemporaryDirectory(prefix="node-core-backup-", dir=self.config.backup_path) as work:
            root = Path(work) / "payload"
            keys_dir = root / "keys"
            keys_dir.mkdir(parents=True, mode=0o700)
            identity_dir = root / "identity"
            identity_dir.mkdir(parents=True, mode=0o700)
            identity = self.kubo.identity()
            keys = self.kubo.list_keys()
            self.kubo.export_identity(identity_dir / "kubo-identity.json")
            for name in keys:
                self.kubo.export_key(name, keys_dir / f"{name}.key")
            (root / "manifest.json").write_bytes(
                serialize_manifest(create_manifest(
                    kubo_version=identity.version,
                    peer_id=identity.peer_id,
                    keys=keys,
                ))
            )
            archive = Path(work) / "payload.tar"
            with tarfile.open(archive, "w") as tar:
                for item in root.rglob("*"):
                    tar.add(item, arcname=item.relative_to(root))
            self.encryption.encrypt_with_passphrase(archive, target, passphrase)

        if not target.is_file() or target.stat().st_size == 0:
            raise RuntimeError("Encrypted backup was not created.")
        target.chmod(0o600)
        self._record_history(target, identity.peer_id)
        return target

    def verify_backup(self, path: Path, passphrase: str) -> dict[str, object]:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        with tempfile.TemporaryDirectory(prefix="node-core-verify-") as work:
            archive = Path(work) / "payload.tar"
            self.encryption.decrypt_with_passphrase(path, archive, passphrase)
            with tarfile.open(archive, "r:") as tar:
                members = tar.getnames()
                manifest_member = tar.getmember("manifest.json")
                manifest = json.loads(tar.extractfile(manifest_member).read().decode("utf-8"))
                key_members = [name for name in members if name.startswith("keys/") and name.endswith(".key")]
        return {
            "valid": "node-core-backup" == manifest.get("format") and manifest.get("version") == 1,
            "manifest": manifest,
            "key_count": len(key_members),
            "identity_present": "identity/kubo-identity.json" in members,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def upload_to_pinata(self, path: Path) -> dict[str, object]:
        result = self.pinata.upload_file(Path(path))
        history = []
        if self.config.backup_history_path.exists():
            history = json.loads(self.config.backup_history_path.read_text(encoding="utf-8"))
        history.append({
            "created_at": datetime.now(timezone.utc).isoformat(),
            "path": str(path),
            "cid": result["cid"],
            "provider": "pinata",
            "encrypted": True,
        })
        self.config.backup_history_path.write_text(
            json.dumps(history, indent=2) + "\n", encoding="utf-8"
        )
        self.config.backup_history_path.chmod(0o600)
        return result

    def _record_history(self, path: Path, peer_id: str | None) -> None:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        record = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "path": str(path),
            "sha256": digest,
            "encrypted": True,
            "peer_id": peer_id,
        }
        history = []
        if self.config.backup_history_path.exists():
            history = json.loads(self.config.backup_history_path.read_text(encoding="utf-8"))
        history.append(record)
        self.config.backup_history_path.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
        self.config.backup_history_path.chmod(0o600)
