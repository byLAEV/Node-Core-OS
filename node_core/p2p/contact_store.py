"""Local contact book mapping Bitcoin addresses to Node Core OS node IDs.

A Bitcoin address is a contact alias only. It does not reveal a peer endpoint,
prove address ownership, or replace certificate-based peer authentication.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any


class P2PContactError(ValueError):
    """Raised when a contact record is invalid or conflicts with a saved record."""


def validate_bitcoin_address(address: str) -> str:
    """Accept common mainnet legacy, SegWit, and Taproot address encodings."""
    if not isinstance(address, str):
        raise P2PContactError("Bitcoin address must be text.")
    address = address.strip()
    if not 14 <= len(address) <= 90 or any(char.isspace() for char in address):
        raise P2PContactError("Bitcoin address length or whitespace is invalid.")
    if address.startswith(("1", "3")):
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        if not 26 <= len(address) <= 35 or any(char not in alphabet for char in address):
            raise P2PContactError("Invalid Base58 Bitcoin address format.")
        return address
    lower = address.lower()
    if lower.startswith(("bc1q", "bc1p")):
        if address != lower or not 14 <= len(address) <= 90:
            raise P2PContactError("Invalid Bech32 Bitcoin address format.")
        alphabet = "023456789acdefghjklmnpqrstuvwxyz"
        if any(char not in alphabet for char in address[4:]):
            raise P2PContactError("Invalid Bech32 Bitcoin address characters.")
        return address
    raise P2PContactError("Unsupported Bitcoin address format (mainnet only).")


def validate_node_id(node_id: str) -> str:
    if (
        not isinstance(node_id, str)
        or len(node_id) != 71
        or not node_id.startswith("sha256:")
        or any(char not in "0123456789abcdef" for char in node_id[7:])
    ):
        raise P2PContactError("Node ID must use sha256:<64 lowercase hexadecimal characters>.")
    return node_id


class P2PContactStore:
    """Persist explicit user-created Bitcoin-address-to-node contact mappings."""

    SCHEMA_VERSION = 1

    def __init__(self, data_dir: Path) -> None:
        self.path = Path(data_dir).expanduser() / "p2p" / "contacts.json"

    def list_contacts(self) -> list[dict[str, Any]]:
        data = self._load()
        return [dict(data["contacts"][address]) for address in sorted(data["contacts"])]

    def get_by_bitcoin_address(self, address: str) -> dict[str, Any] | None:
        address = validate_bitcoin_address(address)
        record = self._load()["contacts"].get(address)
        return dict(record) if record else None

    def save_contact(
        self,
        *,
        bitcoin_address: str,
        node_id: str,
        host: str,
        port: int,
        label: str = "",
    ) -> dict[str, Any]:
        address = validate_bitcoin_address(bitcoin_address)
        node_id = validate_node_id(node_id)
        if not isinstance(host, str) or not host.strip() or len(host) > 255:
            raise P2PContactError("A reachable host or IP address is required.")
        if any(char.isspace() for char in host):
            raise P2PContactError("Host must not contain whitespace.")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise P2PContactError("TCP port must be between 1 and 65535.")
        if not isinstance(label, str) or len(label) > 80:
            raise P2PContactError("Contact label must be 80 characters or fewer.")
        data = self._load()
        for saved_address, record in data["contacts"].items():
            if saved_address != address and record.get("node_id") == node_id:
                raise P2PContactError("That Node ID is already saved under another Bitcoin address.")
        record = {
            "bitcoin_address": address,
            "node_id": node_id,
            "host": host.strip(),
            "port": port,
            "label": label.strip(),
        }
        data["contacts"][address] = record
        self._save(data)
        return dict(record)

    def remove_contact(self, bitcoin_address: str) -> bool:
        address = validate_bitcoin_address(bitcoin_address)
        data = self._load()
        if address not in data["contacts"]:
            return False
        del data["contacts"][address]
        self._save(data)
        return True

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": self.SCHEMA_VERSION, "contacts": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise P2PContactError("Contact store is unreadable or invalid JSON.") from exc
        if (
            not isinstance(data, dict)
            or data.get("schema_version") != self.SCHEMA_VERSION
            or not isinstance(data.get("contacts"), dict)
        ):
            raise P2PContactError("Unsupported or malformed contact store schema.")
        for address, record in data["contacts"].items():
            validate_bitcoin_address(address)
            if not isinstance(record, dict) or record.get("bitcoin_address") != address:
                raise P2PContactError("Contact store contains a malformed record.")
            validate_node_id(record.get("node_id"))
            if not isinstance(record.get("host"), str) or not isinstance(record.get("port"), int):
                raise P2PContactError("Contact endpoint is malformed.")
        return data

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass
        fd, temporary_path = tempfile.mkstemp(prefix=".contacts-", dir=self.path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=True, indent=2, sort_keys=True)
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
