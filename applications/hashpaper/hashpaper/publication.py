"""Kubo/IPFS publication adapter using Node Core OS content interfaces."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any


class PublicationError(RuntimeError):
    """Raised when package publication or verification fails."""


@dataclass(frozen=True)
class PublicationResult:
    cid: str
    name: str
    size_bytes: int
    content_verified: bool
    pinned: bool
    published: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "cid": self.cid,
            "name": self.name,
            "size_bytes": self.size_bytes,
            "sha256": None,
            "content_verified": self.content_verified,
            "pinned": self.pinned,
            "published": self.published,
        }


class HashPaperPublisher:
    """Publish only after the caller has explicitly confirmed public disclosure.

    `runtime` must be a booted NodeRuntime whose Kubo and ContentManager interfaces
    have been constructed by Node Core OS. This adapter never talks directly to the
    administrative Kubo RPC and never claims success without retrieving the CID.
    """

    def __init__(self, runtime: Any) -> None:
        if not hasattr(runtime, "kubo") or not hasattr(runtime, "content"):
            raise PublicationError("A Node Core OS runtime with Kubo and ContentManager is required.")
        self.runtime = runtime

    def publish_package(self, package_path: Path, *, confirmed_publication: bool) -> PublicationResult:
        if not confirmed_publication:
            raise PublicationError("Publication cancelled: explicit user confirmation is required.")

        source = Path(package_path).expanduser()
        if not source.is_file():
            raise PublicationError(f"Package file does not exist: {source}")
        original_bytes = source.read_bytes()
        expected_sha256 = hashlib.sha256(original_bytes).hexdigest()

        status = self.runtime.kubo.status()
        if not status.running:
            raise PublicationError("Kubo is not running. Start Node Core OS/Kubo before publishing.")

        try:
            record = self.runtime.content.add(source, pin=False)
            retrieved = self.runtime.kubo.cat(record.cid)
            if retrieved != original_bytes:
                raise PublicationError(
                    f"Content retrieved by CID {record.cid} does not match the local package bytes."
                )
            if hashlib.sha256(retrieved).hexdigest() != expected_sha256:
                raise PublicationError("SHA-256 mismatch after retrieving the package from Kubo.")

            self.runtime.content.publish(record.cid, pin=True)
            pin_keys = self.runtime.kubo.pin_list()
            pinned = record.cid in pin_keys
            if not pinned:
                raise PublicationError(
                    f"Content was added and retrieved, but pin state could not be confirmed for {record.cid}."
                )
            return PublicationResult(
                cid=record.cid,
                name=record.name,
                size_bytes=record.size,
                content_verified=True,
                pinned=True,
                published=True,
            )
        except PublicationError:
            raise
        except Exception as exc:
            raise PublicationError(f"Node Core Kubo/IPFS publication failed: {exc}") from exc
