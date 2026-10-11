"""Minimal public identity-association announcements and shared reports.

Only the public Kubo peer ID and a boolean declaration are published. Identity
profile fields and document contents are never serialized by this module.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4


PROTOCOL = "node-core-identity-presence/1.0"
REPORT_PROTOCOL = "node-core-network-report/1.0"


class IdentityPresenceError(RuntimeError):
    """Raised when an identity-presence operation cannot be completed."""


class IdentityPresence:
    """Store declarations locally and exchange them by sharing IPFS CIDs."""

    def __init__(self, data_dir: Path, identity_profile: Any, network: Any, kubo: Any):
        self.data_dir = Path(data_dir)
        self.identity_profile = identity_profile
        self.network = network
        self.kubo = kubo
        self.root = self.data_dir / "identity-presence"
        self.announcements_dir = self.root / "announcements"
        self.incoming_dir = self.root / "incoming"
        self.reports_dir = self.root / "reports"
        self.current_report_path = self.reports_dir / "current.json"
        self.state_path = self.root / "state.json"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _ensure_directories(self) -> None:
        for directory in (
            self.announcements_dir, self.incoming_dir, self.reports_dir
        ):
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IdentityPresenceError(f"Cannot read JSON file {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise IdentityPresenceError("Expected a JSON object.")
        return value

    def announce(self) -> dict[str, Any]:
        """Create a declaration using this node's real ID and local association."""
        self._ensure_directories()
        node_id = self.network.identity().peer_id
        profile = self.identity_profile.load()
        associated = bool(profile and profile.get("node_id") == node_id)
        payload = {
            "protocol": PROTOCOL,
            "message_type": "identity_association",
            "node_id": node_id,
            "identity_associated": associated,
            "claim_status": "announced_not_verified",
            "created_at": self._now(),
        }
        self._write_json(self.announcements_dir / f"{node_id}.json", payload)
        return payload

    def import_announcement(self, cid: str) -> dict[str, Any]:
        """Fetch one public declaration by CID, validate it, and save it locally."""
        self._ensure_directories()
        value = cid.strip()
        if not value:
            raise IdentityPresenceError("CID cannot be empty.")
        try:
            raw = self.kubo.cat(value)
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise IdentityPresenceError(f"Could not retrieve declaration by CID: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("protocol") != PROTOCOL:
            raise IdentityPresenceError("CID does not contain a supported identity declaration.")
        node_id = payload.get("node_id")
        if not isinstance(node_id, str) or not node_id or "/" in node_id:
            raise IdentityPresenceError("Declaration has an invalid public node ID.")
        if not isinstance(payload.get("identity_associated"), bool):
            raise IdentityPresenceError("Declaration must contain a boolean identity_associated field.")
        if payload.get("claim_status") != "announced_not_verified":
            raise IdentityPresenceError("Declaration has an unsupported claim status.")
        self._write_json(self.incoming_dir / f"{node_id}.json", payload)
        return payload

    def _all_announcements(self) -> list[dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        for directory in (self.announcements_dir, self.incoming_dir):
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.json")):
                payload = self._read_json(path)
                if payload.get("protocol") != PROTOCOL:
                    continue
                node_id = payload.get("node_id")
                if not isinstance(node_id, str) or not node_id:
                    continue
                if not isinstance(payload.get("identity_associated"), bool):
                    continue
                # A repeated announcement for a node never increases its count.
                records[node_id] = payload
        return [records[node_id] for node_id in sorted(records)]

    def create_report(self) -> dict[str, Any]:
        """Create a report from currently known declarations and save it locally."""
        self._ensure_directories()
        announcements = self._all_announcements()
        local_id = self.network.identity().peer_id
        node_ids = sorted({item["node_id"] for item in announcements})
        report = {
            "protocol": REPORT_PROTOCOL,
            "report_reference_id": str(uuid4()),
            "report_type": "identity_association_statistics",
            "created_at": self._now(),
            "report_creator_node_id": local_id,
            "known_nodes": len(node_ids),
            "connected_nodes": len(set(self.network.connected_peers()) | {local_id}),
            "identity_associations_announced": sum(
                1 for item in announcements if item["identity_associated"]
            ),
            "identity_documents_transmitted": 0,
            "personal_identity_fields_transmitted": 0,
            "announcements": announcements,
        }
        self._write_json(self.current_report_path, report)
        return report

    def publish_report(self) -> dict[str, Any]:
        """Publish and pin the current report; verify pin state before returning."""
        if not self.current_report_path.is_file():
            self.create_report()
        result = self.kubo.add_file(self.current_report_path, pin=True)
        try:
            pinned = result.cid in self.kubo.pin_list()
        except Exception as exc:
            raise IdentityPresenceError(f"Report was added but pin status could not be checked: {exc}") from exc
        if not pinned:
            raise IdentityPresenceError(f"Report CID {result.cid} is not pinned on this node.")
        state = {
            "report_reference_id": self._read_json(self.current_report_path).get("report_reference_id"),
            "report_cid": result.cid,
            "local_report_path": str(self.current_report_path),
            "pinned_locally": True,
            "updated_at": self._now(),
        }
        self._write_json(self.state_path, state)
        return state

    def import_report(self, cid: str) -> dict[str, Any]:
        """Fetch a report CID, verify its schema, pin it, and save identical bytes."""
        self._ensure_directories()
        value = cid.strip()
        if not value:
            raise IdentityPresenceError("CID cannot be empty.")
        try:
            raw = self.kubo.cat(value)
            report = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise IdentityPresenceError(f"Could not retrieve report by CID: {exc}") from exc
        if not isinstance(report, dict) or report.get("protocol") != REPORT_PROTOCOL:
            raise IdentityPresenceError("CID does not contain a supported Node Core report.")
        required = (
            "report_reference_id", "known_nodes", "connected_nodes",
            "identity_associations_announced", "announcements",
        )
        if any(key not in report for key in required):
            raise IdentityPresenceError("Report is missing required fields.")
        if not isinstance(report["announcements"], list):
            raise IdentityPresenceError("Report announcements must be a list.")
        for announcement in report["announcements"]:
            if (
                not isinstance(announcement, dict)
                or announcement.get("protocol") != PROTOCOL
                or not isinstance(announcement.get("node_id"), str)
                or not isinstance(announcement.get("identity_associated"), bool)
            ):
                raise IdentityPresenceError("Report contains an invalid announcement.")
        target = self.reports_dir / f"{report['report_reference_id']}.json"
        target.write_bytes(raw)
        self.current_report_path.write_bytes(raw)
        try:
            self.kubo.pin_add(value)
            pinned = value in self.kubo.pin_list()
        except Exception as exc:
            raise IdentityPresenceError(f"Report saved locally but pin verification failed: {exc}") from exc
        if not pinned:
            raise IdentityPresenceError(f"Report CID {value} is not pinned on this node.")
        state = {
            "report_reference_id": report["report_reference_id"],
            "report_cid": value,
            "local_report_path": str(self.current_report_path),
            "pinned_locally": True,
            "updated_at": self._now(),
        }
        self._write_json(self.state_path, state)
        return state

    def status(self) -> dict[str, Any]:
        """Return local evidence and current report pin status."""
        report = self._read_json(self.current_report_path) if self.current_report_path.is_file() else None
        state = self._read_json(self.state_path) if self.state_path.is_file() else {}
        return {
            "announcement_count": len(self._all_announcements()),
            "report": report,
            "state": state,
        }
