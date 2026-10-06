"""Kubo/IPFS integration boundary.

The adapter is intentionally small: Node Core owns the abstraction while Kubo
remains an infrastructure service managed by BIOS.
"""

from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import urlopen


@dataclass
class IPFSClient:
    api: str

    def status(self, timeout: float = 1.5) -> bool:
        try:
            with urlopen(f"{self.api.rstrip('/')}/api/v0/id", timeout=timeout):
                return True
        except (OSError, URLError):
            return False

    def add(self, path: str) -> None:
        raise NotImplementedError("Kubo add integration is the next implementation milestone.")

    def retrieve(self, cid: str) -> None:
        raise NotImplementedError("CID retrieval is the next implementation milestone.")
