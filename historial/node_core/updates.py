"""Check the installed menu version against the public GitHub repository."""

from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import os
import re

VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"
DEFAULT_VERSION_URL = "https://raw.githubusercontent.com/byLAEV/Node-Core-OS/main/VERSION"
VERSION_PATTERN = re.compile(r"v?\d+(?:\.\d+){1,3}")


@dataclass(frozen=True)
class UpdateStatus:
    local_version: str
    remote_version: str
    available: bool
    checked: bool
    message: str = ""


def _read_local_version() -> str:
    try:
        value = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"
    return value or "unknown"


def _version_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.removeprefix("v").split("."))


def check_for_updates(timeout: float = 3.0) -> UpdateStatus:
    """Check GitHub on every menu opening; network errors never block the menu."""
    local_version = _read_local_version()
    url = os.environ.get("NODE_CORE_VERSION_URL", DEFAULT_VERSION_URL)
    request = Request(url, headers={
        "User-Agent": "Node-Core-OS-update-check",
        "Accept": "text/plain",
    })
    try:
        with urlopen(request, timeout=timeout) as response:
            remote_version = response.read(128).decode("utf-8").strip()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return UpdateStatus(
            local_version, "unknown", False, False,
            f"GitHub check failed: {exc.__class__.__name__}",
        )

    if not VERSION_PATTERN.fullmatch(remote_version):
        return UpdateStatus(
            local_version, "unknown", False, False,
            "GitHub returned an invalid VERSION file.",
        )

    available = local_version == "unknown"
    if VERSION_PATTERN.fullmatch(local_version):
        available = _version_key(remote_version) > _version_key(local_version)

    return UpdateStatus(
        local_version=local_version,
        remote_version=remote_version,
        available=available,
        checked=True,
        message="Version check completed.",
    )
