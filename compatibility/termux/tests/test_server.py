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
                assert "async function checkLobbyConnection()" in page
                assert "checkLobbyConnection();" in page
                assert "runBtn.addEventListener('click',runSelected)" in page
                assert "fetch('/health'" in page
                assert headers.get("Cache-Control") == "no-store"
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
                if tls_expected:
                    assert authorized_result["status"] == "error", authorized_result
                    assert "Package kind" in authorized_result["message"], authorized_result
                else:
                    assert authorized_result["status"] == "forbidden", authorized_result
                    assert "requires HTTPS" in authorized_result["message"], authorized_result
                print("Session token injection, security headers and HTTPS-only package API authorization: PASS")

                catalog_response = request_json(base_url + "/api/certificates", tls_expected)
                assert catalog_response["catalog_version"] == "1.0.0", catalog_response
                assert len(catalog_response["security_profiles"]) == 8, catalog_response
                assert all(not item["installable_certificate"] for item in catalog_response["security_profiles"])
                print("Read-only certificate catalog endpoint: PASS")

                commands = request_json(base_url + "/api/termux/commands", tls_expected)
                command_ids = {item["id"] for item in commands["commands"]}
                assert "working-directory" in command_ids, commands
                assert commands["execution_policy"]["allowlist_only"] is True
                assert commands["execution_policy"]["shell_interpretation"] is False
                print("Read-only Termux command catalog and execution policy: PASS")

                if tls_expected:
                    execute = urllib.request.Request(
                        base_url + "/api/termux/execute",
                        data=json.dumps({"command_id": "working-directory"}).encode("utf-8"),
                        headers={
                            "Content-Type": "application/json",
                            "Origin": base_url,
                            "X-Node-Core-Lobby-Token": config["token"],
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(execute, timeout=3.0, context=context) as response:
                        started = json.loads(response.read().decode("utf-8"))
                    assert started["status"] == "started", started
                    job_id = started["job"]["job_id"]
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        output_request = urllib.request.Request(
                            base_url + "/api/termux/output",
                            data=json.dumps({"job_id": job_id}).encode("utf-8"),
                            headers={
                                "Content-Type": "application/json",
                                "Origin": base_url,
                                "X-Node-Core-Lobby-Token": config["token"],
                            },
                            method="POST",
                        )
                        with urllib.request.urlopen(output_request, timeout=2.0, context=context) as response:
                            output_result = json.loads(response.read().decode("utf-8"))
                        job = output_result["job"]
                        if job["status"] != "running":
                            break
                        time.sleep(0.05)
                    assert job["status"] == "completed", job
                    assert job["returncode"] == 0, job
                    assert job["output"].strip(), job
                    invalid = urllib.request.Request(
                        base_url + "/api/termux/execute",
                        data=b'{"command_id":"arbitrary-shell"}',
                        headers={
                            "Content-Type": "application/json",
                            "Origin": base_url,
                            "X-Node-Core-Lobby-Token": config["token"],
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(invalid, timeout=2.0, context=context) as response:
                        invalid_result = json.loads(response.read().decode("utf-8"))
                    assert invalid_result["status"] == "error", invalid_result
                    print("Authenticated Termux command execution, live output and allowlist enforcement: PASS")

                if tls_expected:
                    renew = urllib.request.Request(
                        base_url + "/api/certificates/action",
                        data=json.dumps({"action": "tls_renew"}).encode("utf-8"),
                        headers={
                            "Content-Type": "application/json",
                            "Origin": base_url,
                            "X-Node-Core-Lobby-Token": config["token"],
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(renew, timeout=15.0, context=context) as response:
                        renewed = json.loads(response.read().decode("utf-8"))
                    assert renewed["status"] == "success", renewed
                    assert renewed["result"]["restart_required"] is True, renewed
                    assert renewed["result"]["after"]["status"] in ("valid", "valid_self_signed"), renewed
                    print("Authenticated Lobby TLS renewal and post-install validation: PASS")

                    recover = urllib.request.Request(
                        base_url + "/api/certificates/action",
                        data=json.dumps({"action": "tls_recover"}).encode("utf-8"),
                        headers={
                            "Content-Type": "application/json",
                            "Origin": base_url,
                            "X-Node-Core-Lobby-Token": config["token"],
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(recover, timeout=15.0, context=context) as response:
                        recovered = json.loads(response.read().decode("utf-8"))
                    assert recovered["status"] == "success", recovered
                    assert recovered["result"]["after"]["status"] in ("valid", "valid_self_signed"), recovered
                    print("Authenticated Lobby TLS backup recovery: PASS")
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
