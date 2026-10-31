"""Replicate GitHub Page records between explicitly trusted Node Core OS peers.

The transport reuses NodePeerService secure messages. Each received record is
persisted under the receiving node's shared storage and deduplicated by
(origin_node_id, record_id). Replicas do not write into the receiving
operator's GitHub repository.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RecordReplicationError(RuntimeError):
    """Raised when a record replication event is invalid or cannot be stored."""


class NodeRecordReplicator:
    SCHEMA = "node-core-os/github-page-record-replication/v1"
    RECORD_SCHEMA = "node-core-os/github-page-record/v1"
    MAX_MESSAGE_BYTES = 16_384

    def __init__(self, data_dir: Path, identity_store: Any) -> None:
        self.data_dir = Path(data_dir).expanduser()
        self.identity_store = identity_store
        self.received_root = self.data_dir / "storage" / "shared" / "github-record-replicas"

    def send_record(
        self,
        peer_service: Any,
        host: str,
        port: int,
        recipient_node_id: str,
        recipient_rsa_public_key_pem: bytes,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """Send one local node record to a trusted peer and return its signed receipt."""
        local_node_id = self.identity_store.initialize()["node_id"]
        self._validate_record(record)
        if record["node_id"] != local_node_id:
            raise RecordReplicationError("Cannot replicate a record owned by a different node.")
        if recipient_node_id == local_node_id:
            raise RecordReplicationError("Cannot replicate a record to the same node.")
        event = {
            "schema": self.SCHEMA,
            "event_id": record["record_id"],
            "origin_node_id": local_node_id,
            "recipient_node_id": recipient_node_id,
            "repository": record["repository"],
            "record": record,
        }
        text = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if len(text.encode("utf-8")) > self.MAX_MESSAGE_BYTES:
            raise RecordReplicationError(
                f"Record exceeds the P2P message limit of {self.MAX_MESSAGE_BYTES} UTF-8 bytes."
            )
        try:
            return peer_service.send_secure_message(
                host,
                port,
                recipient_node_id,
                recipient_rsa_public_key_pem,
                text,
            )
        except Exception as exc:
            raise RecordReplicationError(f"P2P record delivery failed: {exc}") from exc

    def receive_message(self, peer: dict[str, str], message_id: str, text: str) -> bool:
        """Persist a recognized record event; return False for other message types."""
        try:
            event = json.loads(text)
        except (TypeError, json.JSONDecodeError):
            return False
        if not isinstance(event, dict) or event.get("schema") != self.SCHEMA:
            return False

        sender_node_id = peer.get("node_id")
        local_node_id = self.identity_store.initialize()["node_id"]
        if event.get("origin_node_id") != sender_node_id:
            raise RecordReplicationError("Replication origin does not match the authenticated P2P sender.")
        if event.get("recipient_node_id") != local_node_id:
            raise RecordReplicationError("Replication event is addressed to a different node.")

        record = event.get("record")
        self._validate_record(record)
        if record["node_id"] != sender_node_id:
            raise RecordReplicationError("Record owner does not match the authenticated P2P sender.")
        if event.get("event_id") != record["record_id"]:
            raise RecordReplicationError("Replication event ID does not match the record ID.")
        if event.get("repository") != record.get("repository"):
            raise RecordReplicationError("Replication repository does not match the record.")

        origin_directory = self.received_root / sender_node_id.removeprefix("sha256:")
        destination = origin_directory / (record["record_id"] + ".json")
        stored = {
            "schema": self.SCHEMA,
            "event_id": event["event_id"],
            "message_id": message_id,
            "origin_node_id": sender_node_id,
            "replica_node_id": local_node_id,
            "received_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_repository": record["repository"],
            "record": record,
        }
        if destination.is_file():
            existing = json.loads(destination.read_text(encoding="utf-8"))
            if existing.get("record") != record:
                raise RecordReplicationError(
                    "A different record already uses this ID for the same origin node."
                )
            return True

        self._write_json(destination, stored)
        return True

    def list_received(self, origin_node_id: str | None = None) -> list[dict[str, Any]]:
        """List locally persisted replicas, optionally filtered by source node."""
        if origin_node_id is not None:
            if not self._valid_node_id(origin_node_id):
                raise RecordReplicationError("Invalid origin node ID.")
            directories = [self.received_root / origin_node_id.removeprefix("sha256:")]
        else:
            directories = sorted(path for path in self.received_root.glob("*") if path.is_dir()) if self.received_root.exists() else []
        records: list[dict[str, Any]] = []
        for directory in directories:
            for path in sorted(directory.glob("*.json")):
                records.append(json.loads(path.read_text(encoding="utf-8")))
        return records

    @classmethod
    def _validate_record(cls, record: Any) -> None:
        if not isinstance(record, dict):
            raise RecordReplicationError("Replicated record must be a JSON object.")
        if record.get("schema") != cls.RECORD_SCHEMA:
            raise RecordReplicationError("Unsupported GitHub Page record schema.")
        if not isinstance(record.get("record_id"), str):
            raise RecordReplicationError("Record ID is missing.")
        try:
            parsed = uuid.UUID(record["record_id"])
        except (ValueError, TypeError, AttributeError) as exc:
            raise RecordReplicationError("Record ID must be a UUID.") from exc
        if str(parsed) != record["record_id"].lower():
            raise RecordReplicationError("Record ID must use canonical UUID notation.")
        if not cls._valid_node_id(record.get("node_id")):
            raise RecordReplicationError("Record has an invalid origin node ID.")
        if not isinstance(record.get("repository"), str) or "/" not in record["repository"]:
            raise RecordReplicationError("Record repository is missing or invalid.")
        if not isinstance(record.get("fields"), dict):
            raise RecordReplicationError("Record fields must be a JSON object.")

    @staticmethod
    def _valid_node_id(value: Any) -> bool:
        if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
            return False
        return all(char in "0123456789abcdef" for char in value[7:])

    @staticmethod
    def _write_json(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
