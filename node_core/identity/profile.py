"""Local identity profile storage for Node Core OS.

Identity data is private local data. This module never publishes profile content.
"""

from datetime import date, datetime, timezone
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
        """Return an ISO-8601 UTC timestamp."""
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
        full_name: str | None = None,
        alias: str | None = None,
        nationality: str | None = None,
        issuing_country: str | None = None,
        document_type: str | None = None,
        document_number: str | None = None,
        birth_date: str | None = None,
        height_cm: str | int | None = None,
        gender: str | None = None,
    ) -> dict[str, Any]:
        """Save declared fields locally, preserving values omitted during an edit.

        None means "not supplied; preserve the previous value". An empty string
        explicitly clears an optional text field. Required fields cannot be empty.
        This method does not verify the truth of any user-entered value.
        """
        previous = self.load()
        previous = previous or {}

        def text_value(key: str, supplied: str | None) -> str:
            if supplied is None:
                value = previous.get(key, "")
            else:
                value = supplied.strip()
            return value

        normalized = {
            "full_name": text_value("full_name", full_name),
            "alias": text_value("alias", alias),
            "nationality": text_value("nationality", nationality),
            "issuing_country": text_value("issuing_country", issuing_country),
            "document_type": text_value("document_type", document_type),
            "document_number": text_value("document_number", document_number),
            "birth_date": text_value("birth_date", birth_date),
            "gender": text_value("gender", gender),
        }
        for key in ("full_name", "issuing_country", "document_type", "document_number"):
            if not normalized[key]:
                raise ValueError(f"{key.replace('_', ' ').capitalize()} is required.")

        if normalized["birth_date"]:
            try:
                parsed_birth_date = date.fromisoformat(normalized["birth_date"])
            except ValueError as exc:
                raise ValueError("Birth date must be a valid date in YYYY-MM-DD format.") from exc
            if parsed_birth_date.isoformat() != normalized["birth_date"]:
                raise ValueError("Birth date must use YYYY-MM-DD format.")
            if parsed_birth_date > date.today():
                raise ValueError("Birth date cannot be in the future.")

        if height_cm is None:
            parsed_height = previous.get("height_cm")
        elif isinstance(height_cm, str) and not height_cm.strip():
            parsed_height = None
        else:
            try:
                parsed_height = int(str(height_cm).strip())
            except ValueError as exc:
                raise ValueError("Height must be entered as a whole number of centimeters.") from exc
            if not 1 <= parsed_height <= 300:
                raise ValueError("Height must be between 1 and 300 centimeters.")

        now = self._now()
        payload: dict[str, Any] = {
            "schema_version": 1,
            "identity_id": previous.get("identity_id") or str(uuid.uuid4()),
            "full_name": normalized["full_name"],
            "alias": normalized["alias"],
            "nationality": normalized["nationality"],
            "issuing_country": normalized["issuing_country"],
            "document_type": normalized["document_type"],
            "document_number": normalized["document_number"],
            "birth_date": normalized["birth_date"],
            "height_cm": parsed_height,
            "gender": normalized["gender"],
            "identity_status": "declared",
            "node_id": previous.get("node_id"),
            "created_at": previous.get("created_at") or now,
            "updated_at": now,
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
