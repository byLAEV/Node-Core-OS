#!/usr/bin/env python3
"""Local integration test for the read-only Termux Lobby HTTP server."""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

SERVER = pathlib.Path(sys.argv[1]).resolve()
PORT = 18765


def request_json(url: str, use_tls: bool) -> dict:
    context = ssl._create_unverified_context() if use_tls else None
    with urllib.request.urlopen(url, timeout=1.0, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for(url: str, use_tls: bool, process: subprocess.Popen, log: pathlib.Path) -> dict:
    deadline = time.monotonic() + 12
    last_error = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Lobby server exited early: " + log.read_text(errors="replace"))
        try:
            return request_json(url, use_tls)
        except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            time.sleep(0.2)
    raise RuntimeError("Lobby health endpoint timed out: " + repr(last_error))


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main() -> int:
    if not SERVER.is_file():
        raise SystemExit("server.py not found: " + str(SERVER))
    with tempfile.TemporaryDirectory(prefix="node-core-lobby-test-") as temp:
        home = pathlib.Path(temp)
        state = home / ".node-core" / "lobby"
        state.mkdir(parents=True)
        config = {
            "bind": "127.0.0.1",
            "port": PORT,
            "token": "integration-test-only-token-long-enough-for-local-tests",
            "https": True,
        }
        config_path = state / "server.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        log = state / "server-test.log"
        env = os.environ.copy()
        env["HOME"] = str(home)
        env.pop("TERMUX_VERSION", None)
        env.pop("PREFIX", None)

        with log.open("w", encoding="utf-8") as output:
            process = subprocess.Popen(
                [sys.executable, str(SERVER)],
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            try:
                tls_expected = shutil.which("openssl") is not None
                if tls_expected:
                    result = wait_for(
                        f"https://127.0.0.1:{PORT}/health", True, process, log
                    )
                    assert result["transport"] == "https", result
                    status = request_json(
                        f"https://127.0.0.1:{PORT}/api/status", True
                    )
                else:
                    result = wait_for(
                        f"http://127.0.0.1:{PORT}/health", False, process, log
                    )
                    assert result["transport"] == "http", result
                    status = request_json(
                        f"http://127.0.0.1:{PORT}/api/status", False
                    )
                assert status["status"] == "running", status
                print("HTTPS preferred startup and status API: PASS" if tls_expected
                      else "HTTP fallback startup and status API: PASS")

                base_url = f"{'https' if tls_expected else 'http'}://127.0.0.1:{PORT}"
                context = ssl._create_unverified_context() if tls_expected else None
                with urllib.request.urlopen(base_url + "/", timeout=2.0, context=context) as response:
                    page = response.read().decode("utf-8")
                    headers = response.headers
                assert "window.NODE_CORE_LOBBY_SESSION" in page
                assert headers.get("Content-Security-Policy")
                assert headers.get("X-Frame-Options") == "DENY"

                denied = urllib.request.Request(
                    base_url + "/api/packages/prepare",
                    data=b'{"kind":"update"}',
                    headers={"Content-Type": "application/json", "Origin": base_url},
                    method="POST",
                )
                with urllib.request.urlopen(denied, timeout=2.0, context=context) as response:
                    denied_result = json.loads(response.read().decode("utf-8"))
                assert denied_result["status"] == "forbidden", denied_result

                authorized = urllib.request.Request(
                    base_url + "/api/packages/prepare",
                    data=b'{"kind":"invalid"}',
                    headers={
                        "Content-Type": "application/json",
                        "Origin": base_url,
                        "X-Node-Core-Lobby-Token": config["token"],
                    },
                    method="POST",
                )
                with urllib.request.urlopen(authorized, timeout=2.0, context=context) as response:
                    authorized_result = json.loads(response.read().decode("utf-8"))
                assert authorized_result["status"] == "error", authorized_result
                assert "Package kind" in authorized_result["message"], authorized_result
                print("Session token injection, security headers and package API authorization: PASS")
            finally:
                stop(process)

        config["https"] = False
        config_path.write_text(json.dumps(config), encoding="utf-8")
        with log.open("a", encoding="utf-8") as output:
            process = subprocess.Popen(
                [sys.executable, str(SERVER)],
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            try:
                result = wait_for(
                    f"http://127.0.0.1:{PORT}/health", False, process, log
                )
                assert result["transport"] == "http", result
                print("Explicit HTTP loopback mode: PASS")
            finally:
                stop(process)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
