"""Local registry for generic entity identities and their node references.

This registry distinguishes an entity identity from a technical node, credential,
identity document, and evidence record. It stores references, not raw identity
documents, and never publishes data to Kubo/IPFS.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import uuid
from typing import Any


class EntityIdentityRegistryError(RuntimeError):
    """Raised when an entity identity registry operation cannot be completed."""


class EntityIdentityRegistry:
    """Persist generic entity identities, node links, and evidence references locally.

    The registry is a local data model, not a civil-identity verification service,
    distributed consensus engine, credential issuer, or IPFS publisher.
    """

    SCHEMA_VERSION = 1
    ENTITY_TYPES = frozenset(
        {"person", "organization", "device", "object", "service", "program", "resource", "other"}
    )
    EVIDENCE_TYPES = frozenset(
        {"identity_document", "credential", "device_attestation", "ownership_record", "other"}
    )
    NODE_RELATIONSHIPS = frozenset(
        {"operated_by", "controlled_by", "associated_with", "serves", "represents", "other"}
    )

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir).expanduser()
        self.identity_dir = self.data_dir / "identity"
        self.path = self.identity_dir / "entity-registry.json"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def register_entity(
        self,
        entity_type: str,
        *,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        """Register an entity without asserting that its declared identity is verified."""
        if entity_type not in self.ENTITY_TYPES:
            raise EntityIdentityRegistryError("Unsupported entity type.")
        if display_name is not None and (
            not isinstance(display_name, str) or not display_name.strip()
        ):
            raise EntityIdentityRegistryError("Display name must be omitted or non-empty.")

        state = self._read_state()
        now = self._now()
        record: dict[str, Any] = {
            "entity_id": str(uuid.uuid4()),
            "schema_version": self.SCHEMA_VERSION,
            "entity_type": entity_type,
            "display_name": display_name.strip() if display_name is not None else None,
            "status": "active",
            "identity_assurance": "declared",
            "node_links": [],
            "evidence_references": [],
            "created_at": now,
            "updated_at": now,
            "revoked_at": None,
        }
        state["entities"].append(record)
        self._write_state(state)
        return self._copy(record)

    def get_entity(self, entity_id: str) -> dict[str, Any]:
        """Return one entity by its local registry identifier."""
        state = self._read_state()
        for record in state["entities"]:
            if record.get("entity_id") == entity_id:
                return self._copy(record)
        raise EntityIdentityRegistryError("Entity identifier was not found.")

    def list_entities(self, entity_type: str | None = None) -> list[dict[str, Any]]:
        """List entities, optionally filtered by the declared entity type."""
        if entity_type is not None and entity_type not in self.ENTITY_TYPES:
            raise EntityIdentityRegistryError("Unsupported entity type.")
        state = self._read_state()
        records = state["entities"]
        if entity_type is not None:
            records = [item for item in records if item.get("entity_type") == entity_type]
        return [self._copy(item) for item in records]

    def link_node(
        self,
        entity_id: str,
        node_id: str,
        *,
        relationship: str = "associated_with",
    ) -> dict[str, Any]:
        """Record a declared relation to a technical node; this does not prove control."""
        if not isinstance(node_id, str) or not node_id.strip():
            raise EntityIdentityRegistryError("A non-empty node identifier is required.")
        if relationship not in self.NODE_RELATIONSHIPS:
            raise EntityIdentityRegistryError("Unsupported node relationship.")

        state = self._read_state()
        record = self._find_entity(state, entity_id)
        if record["status"] != "active":
            raise EntityIdentityRegistryError("Cannot link a node to a revoked entity.")
        normalized_node_id = node_id.strip()
        for link in record["node_links"]:
            if link.get("node_id") == normalized_node_id and link.get("relationship") == relationship:
                return self._copy(record)

        record["node_links"].append(
            {
                "node_id": normalized_node_id,
                "relationship": relationship,
                "status": "declared",
                "created_at": self._now(),
            }
        )
        record["updated_at"] = self._now()
        self._write_state(state)
        return self._copy(record)

    def unlink_node(
        self,
        entity_id: str,
        node_id: str,
        *,
        relationship: str | None = None,
    ) -> dict[str, Any]:
        """Remove a declared node relation without deleting the entity or node."""
        state = self._read_state()
        record = self._find_entity(state, entity_id)
        before = len(record["node_links"])
        record["node_links"] = [
            link for link in record["node_links"]
            if not (
                link.get("node_id") == node_id
                and (relationship is None or link.get("relationship") == relationship)
            )
        ]
        if len(record["node_links"]) == before:
            raise EntityIdentityRegistryError("Matching node relationship was not found.")
        record["updated_at"] = self._now()
        self._write_state(state)
        return self._copy(record)

    def add_evidence_reference(
        self,
        entity_id: str,
        evidence_type: str,
        reference: str,
        *,
        issuer_reference: str | None = None,
    ) -> dict[str, Any]:
        """Attach a local reference to evidence without storing its raw contents."""
        if evidence_type not in self.EVIDENCE_TYPES:
            raise EntityIdentityRegistryError("Unsupported evidence type.")
        if not isinstance(reference, str) or not reference.strip():
            raise EntityIdentityRegistryError("An evidence reference is required.")
        if issuer_reference is not None and (
            not isinstance(issuer_reference, str) or not issuer_reference.strip()
        ):
            raise EntityIdentityRegistryError("Issuer reference must be omitted or non-empty.")

        state = self._read_state()
        record = self._find_entity(state, entity_id)
        if record["status"] != "active":
            raise EntityIdentityRegistryError("Cannot add evidence to a revoked entity.")
        evidence = {
            "evidence_id": str(uuid.uuid4()),
            "evidence_type": evidence_type,
            "reference": reference.strip(),
            "issuer_reference": issuer_reference.strip() if issuer_reference else None,
            "verification_status": "unverified",
            "created_at": self._now(),
        }
        record["evidence_references"].append(evidence)
        record["updated_at"] = self._now()
        self._write_state(state)
        return self._copy(record)

    def revoke_entity(self, entity_id: str) -> dict[str, Any]:
        """Revoke an entity in this local registry while retaining its audit record."""
        state = self._read_state()
        record = self._find_entity(state, entity_id)
        if record["status"] != "revoked":
            record["status"] = "revoked"
            record["revoked_at"] = self._now()
            record["updated_at"] = record["revoked_at"]
            self._write_state(state)
        return self._copy(record)

    @staticmethod
    def _copy(record: dict[str, Any]) -> dict[str, Any]:
        return json.loads(json.dumps(record))

    @staticmethod
    def _find_entity(state: dict[str, Any], entity_id: str) -> dict[str, Any]:
        if not isinstance(entity_id, str) or not entity_id.strip():
            raise EntityIdentityRegistryError("An entity identifier is required.")
        for record in state["entities"]:
            if record.get("entity_id") == entity_id:
                return record
        raise EntityIdentityRegistryError("Entity identifier was not found.")

    def _read_state(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": self.SCHEMA_VERSION, "entities": []}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EntityIdentityRegistryError("Entity registry cannot be read safely.") from exc
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != self.SCHEMA_VERSION
            or not isinstance(payload.get("entities"), list)
        ):
            raise EntityIdentityRegistryError("Unsupported or invalid entity registry format.")
        for record in payload["entities"]:
            if (
                not isinstance(record, dict)
                or not isinstance(record.get("entity_id"), str)
                or record.get("entity_type") not in self.ENTITY_TYPES
                or not isinstance(record.get("node_links"), list)
                or not isinstance(record.get("evidence_references"), list)
            ):
                raise EntityIdentityRegistryError("Entity registry contains an invalid record.")
        return payload

    def _write_state(self, payload: dict[str, Any]) -> None:
        self.identity_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.identity_dir, 0o700)
        except OSError:
            pass

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".entity-registry-", suffix=".tmp", dir=self.identity_dir
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
            os.replace(temporary_path, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
