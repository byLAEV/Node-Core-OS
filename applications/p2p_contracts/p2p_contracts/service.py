"""Local, append-only BTC exchange request and evidence records.

This prototype persists verifiable JSON documents locally. It does not claim
that records have been propagated to other nodes or published to IPFS.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from uuid import uuid4

REQUEST_SCHEMA = "node-core-os-p2p-contracts/btc-exchange-request/1"
EVIDENCE_SCHEMA = "node-core-os-p2p-contracts/request-evidence/1"
MANIFEST_SCHEMA = "node-core-os-p2p-contracts/application-manifest/1"
FINAL_OUTCOMES = {"exchange_completed", "not_completed", "cancelled", "disputed"}
CONTACT_TYPES = {"email", "phone", "pgp_public_key", "office", "external_protocol", "other"}


class P2PContractsError(RuntimeError):
    """Raised when a local request/evidence operation cannot be completed."""


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    """Return deterministic UTF-8 JSON bytes used for document hashes."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def document_hash(payload: dict[str, Any]) -> str:
    """Hash a payload before adding its external document_hash field."""
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _clean_text(value: str, label: str, maximum: int = 4000) -> str:
    result = value.strip()
    if not result:
        raise ValueError(f"{label} is required.")
    if len(result) > maximum:
        raise ValueError(f"{label} must be {maximum} characters or fewer.")
    return result


def validate_btc_amount(value: str) -> str:
    """Validate BTC as a decimal string without floating-point arithmetic."""
    try:
        amount = Decimal(value.strip())
    except InvalidOperation as exc:
        raise ValueError("BTC amount must be a valid decimal number.") from exc
    if not amount.is_finite() or amount <= 0:
        raise ValueError("BTC amount must be greater than zero.")
    if amount.as_tuple().exponent < -8:
        raise ValueError("BTC amount cannot have more than 8 decimal places.")
    if amount > Decimal("21000000"):
        raise ValueError("BTC amount cannot exceed the Bitcoin supply limit.")
    normalized = format(amount.normalize(), "f")
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def validate_asset_code(value: str) -> str:
    code = _clean_text(value, "Asset or currency to receive", 32).upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{0,31}", code):
        raise ValueError("Asset code contains unsupported characters.")
    if code == "BTC":
        raise ValueError("Choose an asset different from BTC for the receiving side.")
    return code


class P2PContractsService:
    """Create and search local immutable request, evidence and manifest documents."""

    def __init__(self, storage: Any, identity_profile: Any, network: Any) -> None:
        self.storage = storage
        self.identity_profile = identity_profile
        self.network = network
        self.root = self.storage.path("p2p_contracts")
        self.requests_dir = self.root / "requests"
        self.evidence_dir = self.root / "evidence"
        self.manifests_dir = self.root / "manifests"
        self.head_path = self.root / "head.json"

    def _ensure_directories(self) -> None:
        for directory in (self.requests_dir, self.evidence_dir, self.manifests_dir):
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        """Write a local JSON record atomically with owner-only permissions."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temporary_path, 0o600)
            except OSError:
                pass
            os.replace(temporary_path, path)
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise P2PContractsError(f"Unable to read local document {path.name}: {exc}") from exc
        if not isinstance(value, dict):
            raise P2PContractsError(f"Local document {path.name} is not a JSON object.")
        return value

    def _load_head(self) -> dict[str, Any] | None:
        if not self.head_path.is_file():
            return None
        head = self._read_json(self.head_path)
        relative = head.get("manifest_path")
        expected_hash = head.get("manifest_hash")
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            raise P2PContractsError("Local application head is malformed.")
        manifest = self._read_json(self.storage.path(relative))
        payload = {key: value for key, value in manifest.items() if key != "manifest_hash"}
        if document_hash(payload) != expected_hash or manifest.get("manifest_hash") != expected_hash:
            raise P2PContractsError("Current local manifest hash does not match its content.")
        return manifest

    def _publish_new_manifest(self, *, requests: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> dict[str, Any]:
        previous = self._load_head()
        payload: dict[str, Any] = {
            "schema": MANIFEST_SCHEMA,
            "application_id": "node-core-os-p2p-contracts",
            "application_version": "0.1.0-dev",
            "protocol_version": "0.1.0",
            "sequence": (previous["sequence"] + 1) if previous else 1,
            "previous_manifest_hash": previous.get("manifest_hash") if previous else None,
            "created_at": _now(),
            "requests": requests,
            "evidence": evidence,
        }
        digest = document_hash(payload)
        manifest = {**payload, "manifest_hash": digest}
        relative_path = f"p2p_contracts/manifests/manifest-{payload['sequence']:08d}-{digest[:12]}.json"
        self._write_json(self.storage.path(relative_path), manifest)
        self._write_json(self.head_path, {
            "manifest_path": relative_path,
            "manifest_hash": digest,
            "sequence": payload["sequence"],
        })
        return manifest

    @staticmethod
    def _public_identity_fields(profile: dict[str, Any] | None) -> dict[str, Any]:
        if not profile:
            return {}
        allowed = (
            "identity_id", "full_name", "alias", "nationality", "issuing_country",
            "document_type", "document_number", "birth_date", "height_cm", "gender",
            "identity_status",
        )
        return {key: profile[key] for key in allowed if key in profile and profile[key] not in (None, "")}

    def create_btc_exchange_request(
        self, *, btc_amount: str, receive_asset: str, receive_amount: str,
        receive_network: str, description: str, contacts: list[dict[str, str]],
        publish_identity: bool, identity_fields: set[str] | None = None,
    ) -> dict[str, Any]:
        """Persist a BTC-for-asset request and append it to the local manifest."""
        self._ensure_directories()
        amount = validate_btc_amount(btc_amount)
        asset = validate_asset_code(receive_asset)
        wanted_amount = _clean_text(receive_amount, "Amount of asset requested", 128)
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", wanted_amount):
            raise ValueError("Requested asset amount must be a positive decimal string.")
        if Decimal(wanted_amount) <= 0:
            raise ValueError("Requested asset amount must be greater than zero.")
        wanted_amount = format(Decimal(wanted_amount).normalize(), "f")
        network_name = receive_network.strip()
        if len(network_name) > 128:
            raise ValueError("Receiving network must be 128 characters or fewer.")
        details = _clean_text(description, "Request description", 4000)
        if not contacts:
            raise ValueError("Add at least one contact method.")
        normalized_contacts = []
        for item in contacts:
            kind = item.get("type", "").strip().lower()
            value = _clean_text(item.get("value", ""), "Contact value", 1000)
            if kind not in CONTACT_TYPES:
                raise ValueError(f"Unsupported contact type: {kind}")
            if kind == "pgp_public_key":
                if "-----BEGIN PGP PRIVATE KEY BLOCK-----" in value:
                    raise ValueError("A private PGP key must never be entered as a contact method.")
                if "-----BEGIN PGP PUBLIC KEY BLOCK-----" not in value:
                    raise ValueError("PGP contact must contain an armored public key block.")
            normalized_contacts.append({"type": kind, "value": value})
        node_identity = self.network.identity()
        node_id = node_identity.peer_id
        profile = self.identity_profile.load()
        identity = self._public_identity_fields(profile) if publish_identity else {}
        if identity_fields is not None:
            allowed = set(self._public_identity_fields(profile))
            unknown = identity_fields - allowed
            if unknown:
                raise ValueError(f"Unsupported identity fields selected: {', '.join(sorted(unknown))}")
            identity = {key: value for key, value in identity.items() if key in identity_fields}
        request_id = f"request-{uuid4()}"
        payload = {
            "schema": REQUEST_SCHEMA,
            "request_id": request_id,
            "created_at": _now(),
            "request_type": "btc_exchange",
            "status": "open",
            "visibility": "public",
            "requester": {
                "node_id": node_id,
                "addresses": list(node_identity.addresses),
                "identity_ref": profile.get("identity_id") if publish_identity and profile else None,
                "identity_fields": identity,
            },
            "exchange": {
                "give_asset": "BTC",
                "give_amount": amount,
                "receive_asset": asset,
                "receive_amount": wanted_amount,
                "receive_network": network_name or None,
            },
            "description": details,
            "contact_methods": normalized_contacts,
            "financial_disclaimer": "Public request only; it does not execute or verify a transaction.",
        }
        digest = document_hash(payload)
        relative_path = f"p2p_contracts/requests/{request_id}.json"
        self._write_json(self.storage.path(relative_path), {**payload, "document_hash": digest})
        previous = self._load_head()
        requests = list(previous.get("requests", [])) if previous else []
        evidence = list(previous.get("evidence", [])) if previous else []
        requests.append({
            "request_id": request_id, "document_path": relative_path,
            "document_hash": digest, "status": "open", "created_at": payload["created_at"],
        })
        manifest = self._publish_new_manifest(requests=requests, evidence=evidence)
        head = self._read_json(self.head_path)
        return {
            "request_id": request_id, "request_hash": digest,
            "manifest_hash": manifest["manifest_hash"], "manifest_sequence": manifest["sequence"],
            "node_id": node_id, "request_path": str(self.storage.path(relative_path)),
            "manifest_path": str(self.storage.path(head["manifest_path"])),
            "identity_fields_published": sorted(identity), "status": "LOCAL_ONLY",
        }

    def import_remote_requests(self, request_documents: list[dict[str, Any]]) -> dict[str, Any]:
        """Validate and append a batch of public requests received from a peer."""
        self._ensure_directories()
        if not isinstance(request_documents, list) or not request_documents:
            raise ValueError("At least one remote request document is required.")
        previous = self._load_head()
        requests = list(previous.get("requests", [])) if previous else []
        evidence = list(previous.get("evidence", [])) if previous else []
        known = {entry.get("request_id") for entry in requests}
        imported = []
        for document in request_documents:
            if not isinstance(document, dict):
                raise ValueError("Remote request must be a JSON object.")
            digest = document.get("document_hash")
            payload = {key: value for key, value in document.items() if key != "document_hash"}
            if payload.get("schema") != REQUEST_SCHEMA or payload.get("request_type") != "btc_exchange":
                raise ValueError("Remote document is not a supported BTC exchange request.")
            if payload.get("visibility") != "public":
                raise ValueError("Only public requests can be imported by this protocol.")
            request_id = payload.get("request_id")
            if not isinstance(request_id, str) or not re.fullmatch(r"request-[0-9a-fA-F-]{36}", request_id):
                raise ValueError("Remote request ID is malformed.")
            if not isinstance(digest, str) or document_hash(payload) != digest:
                raise P2PContractsError(f"Remote request hash verification failed: {request_id}")
            requester = payload.get("requester")
            if not isinstance(requester, dict) or not isinstance(requester.get("node_id"), str):
                raise ValueError("Remote request does not identify its requesting node.")
            if request_id in known:
                continue
            relative_path = f"p2p_contracts/requests/{request_id}.json"
            destination = self.storage.path(relative_path)
            if destination.exists():
                existing = self._read_json(destination)
                if existing.get("document_hash") != digest:
                    raise P2PContractsError(f"Conflicting request ID already exists locally: {request_id}")
            else:
                self._write_json(destination, document)
            requests.append({
                "request_id": request_id, "document_path": relative_path,
                "document_hash": digest, "status": "open",
                "created_at": payload.get("created_at"),
            })
            known.add(request_id)
            imported.append(request_id)
        if not imported:
            current = self._load_head()
            return {"imported_request_ids": [], "imported_count": 0,
                    "manifest_hash": current.get("manifest_hash") if current else None}
        manifest = self._publish_new_manifest(requests=requests, evidence=evidence)
        return {"imported_request_ids": imported, "imported_count": len(imported),
                "manifest_hash": manifest["manifest_hash"], "manifest_sequence": manifest["sequence"]}

    def create_request_evidence(
        self, *, request_id: str, outcome: str, evidence_type: str,
        description: str, reporter_statement: str, external_reference: str = "",
        target_node_id: str = "", rating: int | None = None,
    ) -> dict[str, Any]:
        """Append a self-reported evidence record linked to an existing request."""
        self._ensure_directories()
        if self.find_request(request_id) is None:
            raise ValueError(f"Request ID was not found in the local application manifest: {request_id}")
        allowed_outcomes = FINAL_OUTCOMES | {"response_received", "offer_received", "no_response"}
        if outcome not in allowed_outcomes:
            raise ValueError("Unsupported evidence outcome.")
        if evidence_type not in {"response", "exchange_result", "follow_up"}:
            raise ValueError("Unsupported evidence type.")
        description_text = _clean_text(description, "Evidence description", 4000)
        statement = _clean_text(reporter_statement, "Reporter statement", 2000)
        reference = external_reference.strip()
        if len(reference) > 1000:
            raise ValueError("External reference must be 1000 characters or fewer.")
        node_id = self.network.identity().peer_id
        if rating is not None and (isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5):
            raise ValueError("Rating must be an integer from 1 to 5.")
        target = target_node_id.strip()
        if len(target) > 200:
            raise ValueError("Target node ID must be 200 characters or fewer.")
        payload = {
            "schema": EVIDENCE_SCHEMA, "evidence_id": f"evidence-{uuid4()}",
            "request_id": request_id, "created_at": _now(), "reporter_node_id": node_id,
            "target_node_id": target or None, "rating": rating,
            "evidence_type": evidence_type, "outcome": outcome,
            "description": description_text, "reporter_statement": statement,
            "external_reference": reference or None,
            "verification_status": "self_reported_unverified",
        }
        digest = document_hash(payload)
        relative_path = f"p2p_contracts/evidence/{payload['evidence_id']}.json"
        self._write_json(self.storage.path(relative_path), {**payload, "document_hash": digest})
        previous = self._load_head()
        requests = list(previous.get("requests", [])) if previous else []
        evidence = list(previous.get("evidence", [])) if previous else []
        evidence.append({
            "evidence_id": payload["evidence_id"], "request_id": request_id,
            "document_path": relative_path, "document_hash": digest,
            "outcome": outcome, "created_at": payload["created_at"],
        })
        for entry in requests:
            if entry["request_id"] == request_id and outcome in FINAL_OUTCOMES:
                entry["status"] = outcome
        manifest = self._publish_new_manifest(requests=requests, evidence=evidence)
        return {
            "evidence_id": payload["evidence_id"], "request_id": request_id,
            "evidence_hash": digest, "manifest_hash": manifest["manifest_hash"],
            "manifest_sequence": manifest["sequence"], "outcome": outcome,
            "verification_status": payload["verification_status"],
        }

    def find_request(self, request_id: str) -> dict[str, Any] | None:
        """Search the current local manifest and verify the request and linked evidence."""
        value = request_id.strip()
        if not value:
            raise ValueError("Enter a request ID.")
        manifest = self._load_head()
        if manifest is None:
            return None
        entry = next((item for item in manifest["requests"] if item["request_id"] == value), None)
        if entry is None:
            return None
        request_doc = self._read_json(self.storage.path(entry["document_path"]))
        request_payload = {key: item for key, item in request_doc.items() if key != "document_hash"}
        if document_hash(request_payload) != entry["document_hash"]:
            raise P2PContractsError("Request document hash does not match the application manifest.")
        related = []
        final_status = "open"
        for item in manifest["evidence"]:
            if item["request_id"] != value:
                continue
            evidence_doc = self._read_json(self.storage.path(item["document_path"]))
            evidence_payload = {key: field for key, field in evidence_doc.items() if key != "document_hash"}
            if document_hash(evidence_payload) != item["document_hash"]:
                raise P2PContractsError("Evidence document hash does not match the application manifest.")
            related.append(evidence_doc)
            if evidence_doc["outcome"] in FINAL_OUTCOMES:
                final_status = evidence_doc["outcome"]
        return {
            "request": request_doc, "request_hash": entry["document_hash"],
            "request_status": final_status, "evidence": related,
            "manifest_hash": manifest["manifest_hash"], "manifest_sequence": manifest["sequence"],
        }

    def current_manifest(self) -> dict[str, Any] | None:
        """Return the verified current local manifest, if one exists."""
        return self._load_head()
