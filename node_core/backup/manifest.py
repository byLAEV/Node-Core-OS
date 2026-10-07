"""Manifest helpers for Node Core OS encrypted backups."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json


@dataclass(frozen=True)
class BackupManifest:
    format: str
    version: int
    created_at: str
    kubo_version: str | None
    peer_id: str | None
    keys: tuple[str, ...]


def create_manifest(*, kubo_version: str | None, peer_id: str | None, keys: list[str]) -> BackupManifest:
    return BackupManifest(
        format="node-core-backup",
        version=1,
        created_at=datetime.now(timezone.utc).isoformat(),
        kubo_version=kubo_version,
        peer_id=peer_id,
        keys=tuple(keys),
    )


def serialize_manifest(manifest: BackupManifest) -> bytes:
    return (json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n").encode("utf-8")
