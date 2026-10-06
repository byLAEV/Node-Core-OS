"""Kubo lifecycle and RPC integration."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class KuboError(RuntimeError):
    """Raised when a Kubo lifecycle or RPC operation fails."""


@dataclass
class KuboStatus:
    installed: bool
    initialized: bool
    running: bool
    peer_id: str | None = None
    version: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class AddedContent:
    cid: str
    name: str
    size: int


class KuboManager:
    def __init__(
        self,
        executable: str,
        repo_path: Path,
        api: str,
        profile: str = "unixfs-v1-2025",
    ) -> None:
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
            raise KuboError(
                f"Kubo executable '{self.executable}' was not found in PATH."
            )
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

    def _rpc(
        self,
        endpoint: str,
        *,
        params: list[tuple[str, str]] | None = None,
        body: bytes | None = None,
        content_type: str | None = None,
        timeout: float = 10.0,
    ) -> bytes:
        query = urlencode(params or [], doseq=True)
        url = f"{self.api}{endpoint}"
        if query:
            url += f"?{query}"

        headers = {}
        if content_type:
            headers["Content-Type"] = content_type

        request = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise KuboError(
                f"Kubo RPC {endpoint} failed ({exc.code}): {detail or exc.reason}"
            ) from exc
        except URLError as exc:
            raise KuboError(f"Kubo RPC {endpoint} unavailable: {exc.reason}") from exc

    def _rpc_json(
        self,
        endpoint: str,
        *,
        params: list[tuple[str, str]] | None = None,
        timeout: float = 10.0,
    ) -> dict:
        data = self._rpc(endpoint, params=params, timeout=timeout)
        try:
            value = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KuboError(f"Invalid JSON response from Kubo: {exc}") from exc
        if not isinstance(value, dict):
            raise KuboError(f"Unexpected JSON response from {endpoint}.")
        return value

    def status(self, timeout: float = 1.5) -> KuboStatus:
        installed = self.is_installed()
        initialized = self.is_initialized()
        if not installed:
            return KuboStatus(False, initialized, False, detail="Kubo not found")
        if not initialized:
            return KuboStatus(
                True, False, False, detail="Kubo repository not initialized"
            )

        try:
            data = self._rpc_json("/api/v0/id", timeout=timeout)
            version = self._rpc_json("/api/v0/version", timeout=timeout)
            return KuboStatus(
                True,
                True,
                True,
                peer_id=data.get("ID"),
                version=version.get("Version"),
            )
        except KuboError:
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
        raise KuboError(
            f"Kubo daemon did not become ready. See {self.log_path}."
        )

    def stop(self) -> None:
        if not self.status().running:
            self._clear_pid()
            return

        self._rpc("/api/v0/shutdown", timeout=3)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if not self.status().running:
                self._clear_pid()
                return
            time.sleep(0.2)
        raise KuboError("Kubo did not stop after the shutdown request.")

    def add_file(
        self,
        path: Path,
        *,
        pin: bool = False,
        cid_version: int = 1,
        cid_base: str = "base32",
    ) -> AddedContent:
        if not path.is_file():
            raise ValueError(f"Content source is not a file: {path}")

        boundary = f"----NodeCoreBoundary{os.urandom(12).hex()}"
        filename = path.name
        file_data = path.read_bytes()

        prefix = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
        suffix = f"\r\n--{boundary}--\r\n".encode("utf-8")

        params = [
            ("pin", "true" if pin else "false"),
            ("cid-version", str(cid_version)),
            ("cid-base", cid_base),
            ("wrap-with-directory", "false"),
        ]
        data = self._rpc(
            "/api/v0/add",
            params=params,
            body=prefix + file_data + suffix,
            content_type=f"multipart/form-data; boundary={boundary}",
            timeout=60.0,
        )

        records = []
        for line in data.decode("utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))

        if not records:
            raise KuboError("Kubo add returned no content record.")

        record = records[-1]
        cid = record.get("Hash")
        if not cid:
            raise KuboError("Kubo add response did not contain a CID.")

        return AddedContent(
            cid=cid,
            name=record.get("Name", filename),
            size=int(record.get("Size", len(file_data))),
        )

    def cat(self, cid: str, timeout: float = 60.0) -> bytes:
        self._validate_cid(cid)
        return self._rpc(
            "/api/v0/cat",
            params=[("arg", cid)],
            timeout=timeout,
        )

    def pin_add(self, cid: str, recursive: bool = True) -> None:
        self._validate_cid(cid)
        self._rpc(
            "/api/v0/pin/add",
            params=[
                ("arg", cid),
                ("recursive", "true" if recursive else "false"),
            ],
            timeout=60.0,
        )

    def pin_remove(self, cid: str, recursive: bool = True) -> None:
        self._validate_cid(cid)
        self._rpc(
            "/api/v0/pin/rm",
            params=[
                ("arg", cid),
                ("recursive", "true" if recursive else "false"),
            ],
            timeout=60.0,
        )

    def pin_list(self) -> dict[str, dict[str, str]]:
        result = self._rpc_json(
            "/api/v0/pin/ls",
            params=[("type", "all"), ("names", "true")],
            timeout=30.0,
        )
        keys = result.get("Keys", {})
        return keys if isinstance(keys, dict) else {}

    @staticmethod
    def _validate_cid(cid: str) -> None:
        value = cid.strip()
        if not value or "/" in value or " " in value:
            raise ValueError("Expected a CID without a local path.")
        if not (value.startswith("bafy") or value.startswith("Qm")):
            raise ValueError(f"Unsupported CID format: {cid}")

    def _clear_pid(self) -> None:
        try:
            self.pid_path.unlink()
        except FileNotFoundError:
            pass
