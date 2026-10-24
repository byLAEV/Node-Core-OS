"""Local-only storage for native P2P text-message requests."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import uuid
from typing import Any


MAX_TEXT_CHARS = 4096
MAX_STORED_MESSAGES = 1000


class P2PMessageStoreError(ValueError):
    """Raised when a message is invalid or the local store is inconsistent."""


class P2PMessageStore:
    """Persist the inbox and acknowledged outbox under the user's data directory."""

    SCHEMA_VERSION = 1

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir).expanduser()
        self.path = self.data_dir / "p2p" / "messages.json"

    def load(self) -> dict[str, Any]:
        """Load and validate local message data; never publishes it to IPFS."""
        if not self.path.exists():
            return {"schema_version": self.SCHEMA_VERSION, "inbox": [], "outbox": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise P2PMessageStoreError("P2P message store is unreadable or invalid JSON.") from exc
        if not isinstance(data, dict) or data.get("schema_version") != self.SCHEMA_VERSION:
            raise P2PMessageStoreError("Unsupported or malformed P2P message store schema.")
        for name in ("inbox", "outbox"):
            records = data.get(name)
            if not isinstance(records, list) or len(records) > MAX_STORED_MESSAGES:
                raise P2PMessageStoreError(f"P2P message store {name} must be a bounded list.")
            if any(not isinstance(record, dict) for record in records):
                raise P2PMessageStoreError(f"P2P message store {name} contains an invalid record.")
        return data

    def record_incoming(
        self,
        *,
        from_node_id: str,
        recipient_node_id: str,
        local_node_id: str,
        request_id: str,
        text: str,
        sent_at: str,
    ) -> dict[str, str]:
        """Store a message as an unread request after checking its authenticated recipient."""
        self._validate_node_id(from_node_id)
        self._validate_node_id(recipient_node_id)
        self._validate_node_id(local_node_id)
        self._validate_request_id(request_id)
        self._validate_text(text)
        self._validate_timestamp(sent_at)
        if recipient_node_id != local_node_id:
            raise P2PMessageStoreError("Message recipient does not match this node's identity.")

        data = self.load()
        for record in data["inbox"]:
            if record.get("from_node_id") == from_node_id and record.get("request_id") == request_id:
                if record.get("text") != text or record.get("sent_at") != sent_at:
                    raise P2PMessageStoreError("Duplicate request ID was reused with different content.")
                return {"message_id": str(record["message_id"]), "status": "received"}

        message_id = uuid.uuid4().hex
        received_at = datetime.now(timezone.utc).isoformat()
        data["inbox"].append({
            "message_id": message_id,
            "request_id": request_id,
            "from_node_id": from_node_id,
            "to_node_id": local_node_id,
            "text": text,
            "sent_at": sent_at,
            "received_at": received_at,
            "status": "pending",
            "read_at": None,
        })
        data["inbox"] = data["inbox"][-MAX_STORED_MESSAGES:]
        self._save(data)
        return {"message_id": message_id, "status": "received"}

    def record_outgoing(
        self,
        *,
        to_node_id: str,
        request_id: str,
        message_id: str,
        text: str,
        sent_at: str,
        received_at: str,
    ) -> dict[str, str]:
        """Record an outgoing message only after the receiver confirms local persistence."""
        self._validate_node_id(to_node_id)
        self._validate_request_id(request_id)
        self._validate_request_id(message_id)
        self._validate_text(text)
        self._validate_timestamp(sent_at)
        self._validate_timestamp(received_at)
        data = self.load()
        for record in data["outbox"]:
            if record.get("request_id") == request_id:
                if record.get("to_node_id") != to_node_id or record.get("text") != text:
                    raise P2PMessageStoreError("Duplicate request ID was reused with different content.")
                return {"message_id": str(record["message_id"]), "status": str(record["status"])}

        data["outbox"].append({
            "message_id": message_id,
            "request_id": request_id,
            "to_node_id": to_node_id,
            "text": text,
            "sent_at": sent_at,
            "received_at": received_at,
            "status": "received",
        })
        data["outbox"] = data["outbox"][-MAX_STORED_MESSAGES:]
        self._save(data)
        return {"message_id": message_id, "status": "received"}

    def list_inbox(self) -> list[dict[str, Any]]:
        """Return a copy of locally received messages in insertion order."""
        return [dict(item) for item in self.load()["inbox"]]

    def list_outbox(self) -> list[dict[str, Any]]:
        """Return a copy of outgoing messages with verified receiver receipts."""
        return [dict(item) for item in self.load()["outbox"]]

    def mark_read(self, message_id: str) -> bool:
        """Mark one local inbox request as read; return False when it does not exist."""
        if not isinstance(message_id, str) or not message_id:
            raise P2PMessageStoreError("Message ID is required.")
        data = self.load()
        for record in data["inbox"]:
            if record.get("message_id") == message_id:
                if record.get("status") != "read":
                    record["status"] = "read"
                    record["read_at"] = datetime.now(timezone.utc).isoformat()
                    self._save(data)
                return True
        return False

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass
        fd, temporary_path = tempfile.mkstemp(prefix=".messages-", dir=self.path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    @staticmethod
    def _validate_node_id(node_id: str) -> None:
        if (
            not isinstance(node_id, str)
            or len(node_id) != 71
            or not node_id.startswith("sha256:")
            or any(char not in "0123456789abcdef" for char in node_id[7:])
        ):
            raise P2PMessageStoreError("Node ID must use sha256:<64 lowercase hexadecimal characters>.")

    @staticmethod
    def _validate_request_id(request_id: str) -> None:
        if (
            not isinstance(request_id, str)
            or not request_id
            or len(request_id) > 128
            or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:" for char in request_id)
        ):
            raise P2PMessageStoreError("Message request ID is invalid.")

    @staticmethod
    def _validate_text(text: str) -> None:
        if not isinstance(text, str) or not text.strip():
            raise P2PMessageStoreError("Message text cannot be empty.")
        if len(text) > MAX_TEXT_CHARS:
            raise P2PMessageStoreError(f"Message text cannot exceed {MAX_TEXT_CHARS} characters.")
        if "\x00" in text:
            raise P2PMessageStoreError("Message text contains a prohibited NUL character.")

    @staticmethod
    def _validate_timestamp(value: str) -> None:
        if not isinstance(value, str) or not value or len(value) > 64:
            raise P2PMessageStoreError("Message timestamp is invalid.")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise P2PMessageStoreError("Message timestamp must use ISO 8601 format.") from exc
