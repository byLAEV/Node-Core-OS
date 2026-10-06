"""Kubo lifecycle and RPC integration."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

class KuboError(RuntimeError):
    """Raised when a Kubo lifecycle operation cannot be completed."""

@dataclass
class KuboStatus:
    installed: bool
    initialized: bool
    running: bool
    peer_id: str | None = None
    version: str | None = None
    detail: str | None = None

class KuboManager:
    def __init__(self, executable: str, repo_path: Path, api: str, profile: str = "unixfs-v1-2025") -> None:
        self.executable = executable
        self.repo_path = repo_path
        self.api = api.rstrip("/")
        self.profile = profile
        self.pid_path = repo_path / "node-core.pid"
        self.log_path = repo_path / "node-core-daemon.log"

    def executable_path(self) -> str | None:
        return shutil.which(self.executable)

    def is_installed(self) -> bool:
        return self.executable_path() is not None

    def is_initialized(self) -> bool:
        return (self.repo_path / "config").is_file()

    def _environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env["IPFS_PATH"] = str(self.repo_path)
        return env

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        if not self.is_installed():
            raise KuboError(f"Kubo executable '{self.executable}' was not found in PATH.")
        return subprocess.run(
            [self.executable, *args],
            env=self._environment(),
            text=True,
            capture_output=True,
            check=True,
        )

    def initialize(self) -> None:
        if self.is_initialized():
            return
        self.repo_path.mkdir(parents=True, exist_ok=True)
        self._run("init")
        if self.profile:
            self._run("config", "profile", "apply", self.profile)

    def _rpc_json(self, endpoint: str, timeout: float) -> dict:
        request = Request(self.api + endpoint, method="POST")
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def status(self, timeout: float = 1.5) -> KuboStatus:
        installed = self.is_installed()
        initialized = self.is_initialized()
        if not installed:
            return KuboStatus(False, initialized, False, detail="Kubo not found")
        if not initialized:
            return KuboStatus(True, False, False, detail="Kubo repository not initialized")
        try:
            data = self._rpc_json("/api/v0/id", timeout)
            version = self._rpc_json("/api/v0/version", timeout)
            return KuboStatus(True, True, True, peer_id=data.get("ID"), version=version.get("Version"))
        except (OSError, HTTPError, URLError, ValueError):
            return KuboStatus(True, True, False)

    def start(self, wait_seconds: float = 8.0) -> None:
        status = self.status()
        if status.running:
            return
        if not status.initialized:
            self.initialize()
        self.repo_path.mkdir(parents=True, exist_ok=True)
        log = self.log_path.open("ab")
        process = subprocess.Popen(
            [self.executable, "daemon"],
            env=self._environment(),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.pid_path.write_text(str(process.pid) + "\n", encoding="utf-8")
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            if self.status().running:
                return
            if process.poll() is not None:
                break
            time.sleep(0.2)
        self._clear_pid()
        raise KuboError(f"Kubo daemon did not become ready. See {self.log_path}.")

    def stop(self) -> None:
        if not self.status().running:
            self._clear_pid()
            return
        request = Request(self.api + "/api/v0/shutdown", method="POST")
        try:
            with urlopen(request, timeout=3):
                pass
        except (OSError, HTTPError, URLError):
            pass
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if not self.status().running:
                self._clear_pid()
                return
            time.sleep(0.2)
        raise KuboError("Kubo did not stop after the shutdown request.")

    def _clear_pid(self) -> None:
        try:
            self.pid_path.unlink()
        except FileNotFoundError:
            pass
