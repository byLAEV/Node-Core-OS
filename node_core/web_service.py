"""Manage the local Node Core Web API as an ordinary-user process."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class NodeWebServiceManager:
    """Start and stop the loopback-only Node Core web API without privilege escalation."""

    def __init__(self, data_dir: Path, app_root: Path) -> None:
        self.data_dir = Path(data_dir)
        self.app_root = Path(app_root)
        self.runtime_dir = self.data_dir / "runtime"
        self.log_path = self.data_dir / "logs" / "web-ui.log"
        self.pid_path = self.runtime_dir / "web-ui.pid"

    @staticmethod
    def _require_user() -> None:
        get_uid = getattr(os, "geteuid", None)
        if get_uid is None or get_uid() == 0:
            raise RuntimeError("Node Core Web API is user-only. Run it as your normal user without sudo or su.")

    def _port(self) -> int:
        raw = os.environ.get("NODE_CORE_WEB_PORT", "8765")
        try:
            port = int(raw)
        except ValueError as exc:
            raise ValueError("NODE_CORE_WEB_PORT must be an integer from 1 to 65535.") from exc
        if not 1 <= port <= 65535:
            raise ValueError("NODE_CORE_WEB_PORT must be an integer from 1 to 65535.")
        return port

    def _pid(self) -> int | None:
        if not self.pid_path.is_file():
            return None
        try:
            pid = int(self.pid_path.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            return None
        if pid <= 1:
            return None
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return None
        except PermissionError:
            return None
        command_line = Path(f"/proc/{pid}/cmdline")
        try:
            command = command_line.read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
        except OSError:
            return None
        return pid if "node_core.web_ui" in command else None

    def status(self) -> dict[str, Any]:
        port = self._port()
        pid = self._pid()
        if pid is None and self.pid_path.exists():
            try:
                self.pid_path.unlink()
            except OSError:
                pass
        return {
            "running": pid is not None,
            "pid": pid,
            "host": "127.0.0.1",
            "port": port,
            "url": f"http://127.0.0.1:{port}/",
            "log_path": str(self.log_path),
        }

    def start(self) -> dict[str, Any]:
        self._require_user()
        current = self.status()
        if current["running"]:
            return current
        if not self.app_root.is_dir() or not (self.app_root / "node_core" / "web_ui.py").is_file():
            raise RuntimeError(f"Installed Node Core web application not found: {self.app_root}")
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        port = self._port()
        environment = os.environ.copy()
        environment["NODE_CORE_DATA_DIR"] = str(self.data_dir)
        environment["NODE_CORE_CONFIG"] = str(self.data_dir / "config.json")
        environment["NODE_CORE_WEB_PORT"] = str(port)
        environment.setdefault("NODE_CORE_WEB_AUTO_START_KUBO", "0")
        with self.log_path.open("ab") as log_file:
            process = subprocess.Popen(
                [sys.executable, "-m", "node_core.web_ui"],
                cwd=self.app_root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
        temporary_pid = self.pid_path.with_suffix(".pid.tmp")
        temporary_pid.write_text(f"{process.pid}\n", encoding="ascii")
        temporary_pid.replace(self.pid_path)
        url = f"http://127.0.0.1:{port}/api/github/binding"
        for _ in range(40):
            if process.poll() is not None:
                break
            try:
                request = urllib.request.Request(url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(request, timeout=1) as response:
                    if response.status == 200:
                        return self.status()
            except (OSError, urllib.error.URLError, TimeoutError):
                time.sleep(0.25)
        self.stop()
        detail = self.read_log()
        raise RuntimeError(f"Node Core Web API did not become ready on port {port}.\n{detail}")

    def stop(self) -> dict[str, Any]:
        self._require_user()
        pid = self._pid()
        if pid is None:
            try:
                self.pid_path.unlink(missing_ok=True)
            except OSError:
                pass
            return self.status()
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        for _ in range(40):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.125)
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            self.pid_path.unlink(missing_ok=True)
        except OSError:
            pass
        return self.status()

    def read_log(self, maximum_lines: int = 80) -> str:
        if not self.log_path.is_file():
            return "No Node Core Web API log has been created."
        lines = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-maximum_lines:])
