"""Local identity profile storage for Node Core OS.

Identity data is private local data. This module never publishes profile content.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import uuid
from typing import Any


class IdentityProfileStore:
    """Persist a declared identity profile in the user's local data directory."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.profile_dir = self.data_dir / "identity"
        self.profile_path = self.profile_dir / "profile.json"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def load(self) -> dict[str, Any] | None:
        """Return the saved profile, or None if the user has not created one."""
        if not self.profile_path.is_file():
            return None
        payload = json.loads(self.profile_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("Unsupported or invalid identity profile format.")
        return payload

    def save_declared_profile(
        self,
        *,
        full_name: str,
        alias: str,
        nationality: str,
        issuing_country: str,
        document_type: str,
        document_number: str,
    ) -> dict[str, Any]:
        """Save user-declared fields locally; this does not verify their truth."""
        fields = {
            "full_name": full_name,
            "alias": alias,
            "nationality": nationality,
            "issuing_country": issuing_country,
            "document_type": document_type,
            "document_number": document_number,
        }
        normalized = {key: value.strip() for key, value in fields.items()}
        for key in ("full_name", "issuing_country", "document_type", "document_number"):
            if not normalized[key]:
                raise ValueError(f"{key.replace('_', ' ').capitalize()} is required.")

        previous = self.load()
        payload: dict[str, Any] = {
            "schema_version": 1,
            "identity_id": (
                previous.get("identity_id", str(uuid.uuid4()))
                if previous
                else str(uuid.uuid4())
            ),
            "full_name": normalized["full_name"],
            "alias": normalized["alias"],
            "nationality": normalized["nationality"],
            "issuing_country": normalized["issuing_country"],
            "document_type": normalized["document_type"],
            "document_number": normalized["document_number"],
            "identity_status": "declared",
            "node_id": previous.get("node_id") if previous else None,
            "created_at": previous.get("created_at", self._now()) if previous else self._now(),
            "updated_at": self._now(),
        }
        self._write_private(payload)
        return payload

    def associate_node(self, node_id: str) -> dict[str, Any]:
        """Explicitly associate the profile with an existing technical node ID."""
        value = node_id.strip()
        if not value:
            raise ValueError("A real node identifier is required for association.")
        profile = self.load()
        if profile is None:
            raise ValueError("Create an identity profile before associating a node.")
        profile["node_id"] = value
        profile["updated_at"] = self._now()
        self._write_private(profile)
        return profile

    def _write_private(self, payload: dict[str, Any]) -> None:
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.profile_dir, 0o700)
        except OSError:
            pass

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".profile-", suffix=".tmp", dir=self.profile_dir
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temporary_path, 0o600)
            except OSError:
                pass
            os.replace(temporary_path, self.profile_path)
            try:
                os.chmod(self.profile_path, 0o600)
            except OSError:
                pass
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
