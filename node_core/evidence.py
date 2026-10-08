"""Basic evidence creation for Node Core OS."""

from dataclasses import dataclass
from datetime import datetime, timezone

from node_core.content import ContentManager, ContentRecord


@dataclass(frozen=True)
class EvidenceResult:
    """Result of creating one text evidence record."""

    path: str
    content: ContentRecord


class EvidenceManager:
    """Create text evidence locally and add the same file to IPFS."""

    def __init__(self, content: ContentManager) -> None:
        self.content = content

    def create_text(self, text: str) -> EvidenceResult:
        if not text.strip():
            raise ValueError("Evidence text cannot be empty.")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        relative_path = f"evidence/evidence_{timestamp}.txt"
        local_path = self.content.storage.write_bytes(
            relative_path,
            text.encode("utf-8"),
        )

        try:
            record = self.content.add(local_path, pin=True)
        except Exception:
            try:
                local_path.unlink()
            except FileNotFoundError:
                pass
            raise

        return EvidenceResult(
            path=str(local_path),
            content=record,
        )
