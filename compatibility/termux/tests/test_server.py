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
import hashlib

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
import urllib.error
import urllib.request

SERVER = pathlib.Path(sys.argv[1]).resolve()
LOBBY_DIR = SERVER.parent
sys.path.insert(0, str(LOBBY_DIR))
from host_environment import detect_host_environment, create_installation_snapshot, read_installation_snapshot
PORT = 18765


def request_json(url: str, use_tls: bool, timeout: float = 1.0) -> dict:
    context = ssl._create_unverified_context() if use_tls else None
    with urllib.request.urlopen(url, timeout=timeout, context=context) as response:
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

        # Mirror the official install-lobby.sh contract: the canonical layout
        # manifest is copied into the private Lobby state directory. The
        # server intentionally does not fall back to a source-tree path.
        manifests = state / "manifests"
        manifests.mkdir(mode=0o700)
        repository_root = SERVER.parents[3]
        canonical_layout = repository_root / "installer" / "layout-manifest.json"
        if not canonical_layout.is_file():
            raise SystemExit("Canonical installer layout manifest is missing: " + str(canonical_layout))
        installed_layout = manifests / "layout-manifest.json"
        shutil.copy2(canonical_layout, installed_layout)
        installed_layout.chmod(0o600)

        # Provide a harmless fake installed launcher so the HTTP integration
        # test can prove that the Lobby PTY starts the installed command, not
        # an assumed development checkout.
        fake_launcher = home / ".node-core" / "bin" / "node-core"
        fake_launcher.parent.mkdir(parents=True, exist_ok=True)
        fake_launcher.write_text(
            "#!/usr/bin/env bash\n"
            "printf 'NODE_CORE_TEST_LAUNCHER_EXECUTED\n'\n"
            "IFS= read -r terminal_input || true\n"
            "printf 'NODE_CORE_TEST_INPUT:%s\n' \"$terminal_input\"\n",
            encoding="utf-8",
        )
        fake_launcher.chmod(0o700)

        host_snapshot = create_installation_snapshot({"TERMUX_VERSION":"0.118-test","PREFIX":"/data/data/com.termux/files/usr","SHELL":"/data/data/com.termux/files/usr/bin/bash"})
        (state / "host-environment.json").write_text(json.dumps(host_snapshot), encoding="utf-8")
        (state / "host-environment.json").chmod(0o600)

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
        # Simulate the Termux runtime marker so first-install guard tests can
        # reach the installer policy without running a real Android installer.
        env["TERMUX_VERSION"] = "0.118-test"
        env["PREFIX"] = "/data/data/com.termux/files/usr"

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
                assert "Generate Report" in page
                assert "Node Core OS Directory Manifest" in page
                assert "/api/layout/manifest" in page
                layout = request_json(base_url + "/api/layout/manifest", tls_expected)
                assert layout["layout_id"] == "node-core-os-user-runtime", layout
                layout_paths = {item["path"] for item in layout["directories"]}
                assert {"app", "bin", "storage", "ipfs", "logs", "runtime", "services", "lobby"} <= layout_paths, layout_paths
                print("Canonical Node Core OS directory manifest endpoint: PASS")
                assert "Copy TXT" in page and "Copy JSON" in page
                assert "Download TXT" in page and "Download JSON" in page
                assert "Share report" in page
                report = request_json(base_url + "/api/report", tls_expected, timeout=20.0)
                assert report["summary"]["total"] == len(report["checks"]), report
                assert report["privacy"]["read_only"] is True, report
                assert "environment" in report and "node_core" in report and "network" in report
                assert report["environment"]["profile"] == "termux"
                environment_api = request_json(base_url + "/api/environment", tls_expected)
                assert environment_api["current"]["profile"] == "termux", environment_api
                assert environment_api["installation_compatibility"]["status"] in ("compatible", "environment_changed_or_unsupported"), environment_api
                assert environment_api["installation_compatibility"]["installed"] is not None, environment_api
                print("Linux host detection, persisted installation environment and compatibility API: PASS")
                print("Official read-only Termux report API and export controls: PASS")
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
                # The fake launcher exists only for the later PTY test. Temporarily
                # remove it so the first-install gate sees a genuinely clean HOME.
                fake_launcher_contents = fake_launcher.read_text(encoding="utf-8")
                fake_launcher.unlink()
                try:
                    install_without_identity = urllib.request.Request(
                        base_url + "/api/packages/execute",
                        data=b'{"kind":"install"}',
                        headers={
                            "Content-Type": "application/json",
                            "Origin": base_url,
                            "X-Node-Core-Lobby-Token": config["token"],
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(install_without_identity, timeout=3.0, context=context) as response:
                        install_locked = json.loads(response.read().decode("utf-8"))
                finally:
                    fake_launcher.write_text(fake_launcher_contents, encoding="utf-8")
                    fake_launcher.chmod(0o700)
                assert install_locked["status"] == "error", install_locked
                assert "Bitcoin" in install_locked["message"] and "locked" in install_locked["message"], install_locked
                print("First installation blocked until verified Bitcoin identity proof: PASS")

                # Verify the public-only Bitcoin identity gate end-to-end.
                if tls_expected:
                    identity_status = request_json(base_url + "/api/identity/bitcoin", True)
                    assert identity_status["status"] == "not_verified", identity_status

                    def identity_post(path, payload):
                        request = urllib.request.Request(
                            base_url + path,
                            data=json.dumps(payload).encode("utf-8"),
                            headers={
                                "Content-Type": "application/json",
                                "Origin": base_url,
                                "X-Node-Core-Lobby-Token": config["token"],
                            },
                            method="POST",
                        )
                        with urllib.request.urlopen(request, timeout=3.0, context=context) as response:
                            return json.loads(response.read().decode("utf-8"))

                    challenge_response = identity_post(
                        "/api/identity/bitcoin/challenge",
                        {"full_name": "Synthetic CI Identity", "document_number": "SYNTHETIC-CI-0001", "nationality": "Costa Rican", "birth_date": "12/05/1990", "height_cm": 178},
                    )
                    assert challenge_response["status"] == "challenge_issued", challenge_response
                    challenge = challenge_response["challenge"]
                    private_key = ec.derive_private_key(1, ec.SECP256K1())
                    public_key = private_key.public_key().public_bytes(
                        serialization.Encoding.X962,
                        serialization.PublicFormat.CompressedPoint,
                    )
                    from bitcoin_identity import encode_p2wpkh_address
                    address = encode_p2wpkh_address(public_key)
                    message_hash = hashlib.sha256(challenge["message"].encode("utf-8")).digest()
                    signature = private_key.sign(
                        message_hash,
                        ec.ECDSA(utils.Prehashed(hashes.SHA256())),
                    )
                    verified = identity_post(
                        "/api/identity/bitcoin/verify",
                        {
                            "challenge_id": challenge["challenge_id"],
                            "public_key_hex": public_key.hex(),
                            "address": address,
                            "signature_hex": signature.hex(),
                        },
                    )
                    assert verified["status"] == "verified", verified
                    assert verified["identity"]["status"] == "control_verified", verified
                    assert verified["identity"]["address"] == address, verified
                    assert verified["identity"]["full_name"] == "Synthetic CI Identity", verified
                    assert verified["identity"]["document_number_masked"] == "********0001", verified
                    assert verified["identity"]["birth_date"] == "12/05/1990", verified
                    assert verified["identity"]["height_cm"] == 178, verified
                    assert verified["identity"]["installation_gate_ready"] is False, verified
                    pending_file = home / ".node-core" / "lobby" / "bitcoin-identity-pending.json"
                    pending_text = pending_file.read_text(encoding="utf-8")
                    assert private_key.private_numbers().private_value.to_bytes(32, "big").hex() not in pending_text
                    assert oct(pending_file.stat().st_mode & 0o777) == "0o600"
                    replay = identity_post(
                        "/api/identity/bitcoin/verify",
                        {
                            "challenge_id": challenge["challenge_id"],
                            "public_key_hex": public_key.hex(),
                            "address": address,
                            "signature_hex": signature.hex(),
                        },
                    )
                    assert replay["status"] == "error", replay
                    identity_post("/api/identity/bitcoin/cancel", {})
                    assert request_json(base_url + "/api/identity/bitcoin", True)["status"] == "not_verified"

                    local_challenge_response = identity_post(
                        "/api/identity/bitcoin/challenge",
                        {"full_name": "Synthetic Local Key Identity", "document_number": "SYNTHETIC-LOCAL-0002", "nationality": "Costa Rican", "birth_date": "08/11/1991", "height_cm": 175},
                    )
                    local_challenge = local_challenge_response["challenge"]
                    local_key_hex = (1).to_bytes(32, "big").hex()
                    local_verified = identity_post(
                        "/api/identity/bitcoin/verify-local-key",
                        {
                            "challenge_id": local_challenge["challenge_id"],
                            "private_key_hex": local_key_hex,
                        },
                    )
                    assert local_verified["status"] == "verified", local_verified
                    assert local_verified["identity"]["address"] == address, local_verified
                    assert local_verified["identity"]["full_name"] == "Synthetic Local Key Identity"
                    assert local_verified["identity"]["document_number_masked"] == "********0002", local_verified
                    assert local_verified["identity"]["installation_gate_ready"] is True, local_verified
                    pending_text = pending_file.read_text(encoding="utf-8")
                    assert local_key_hex not in pending_text
                    assert "private_key_hex" not in pending_text

                    # Simulate the official installer having created the app tree
                    # and the real persistent Ed25519 node identity.
                    app_root = home / ".node-core" / "app"
                    app_root.mkdir(parents=True)
                    (app_root / "node_core").symlink_to(repository_root / "node_core", target_is_directory=True)
                    (app_root / "VERSION").write_text("1.2.3", encoding="utf-8")
                    if str(repository_root) not in sys.path:
                        sys.path.insert(0, str(repository_root))
                    from node_core.identity.entity_registry import EntityIdentityRegistry
                    from node_core.identity.node_identity import NodeIdentityStore
                    from node_core.identity.profile import IdentityProfileStore
                    node_metadata = NodeIdentityStore(home / ".node-core").initialize()

                    association_response = identity_post("/api/identity/bitcoin/associate-node", {})
                    assert association_response["status"] == "associated", association_response
                    association = association_response["association"]
                    assert association["entity_id"] == local_verified["identity"]["entity_id"], association
                    assert association["node_id"] == node_metadata["node_id"], association
                    assert association["node_key_possession_verified"] is True, association
                    assert association["relationship_status"] == "declared", association
                    saved_profile = IdentityProfileStore(home / ".node-core").load()
                    assert saved_profile["full_name"] == "Synthetic Local Key Identity", saved_profile
                    assert saved_profile["document_number"] == "SYNTHETIC-LOCAL-0002", saved_profile
                    assert saved_profile["nationality"] == "Costa Rican", saved_profile
                    assert saved_profile["birth_date"] == "1991-11-08", saved_profile
                    assert saved_profile["height_cm"] == 175, saved_profile
                    assert saved_profile["bitcoin_address"] == address, saved_profile
                    assert saved_profile["node_id"] == node_metadata["node_id"], saved_profile
                    profile_text = IdentityProfileStore(home / ".node-core").profile_path.read_text(encoding="utf-8")
                    assert local_key_hex not in profile_text and "private_key_hex" not in profile_text
                    repeated_association = identity_post("/api/identity/bitcoin/associate-node", {})
                    assert repeated_association["status"] == "associated", repeated_association
                    assert repeated_association["association"]["node_id"] == node_metadata["node_id"], repeated_association
                    identity_status = request_json(base_url + "/api/identity/bitcoin", True)
                    assert identity_status["node_id"] == node_metadata["node_id"], identity_status
                    assert identity_status["node_association_status"] == "associated", identity_status
                    assert identity_status["pending"] is False, identity_status
                    persisted_identity = json.loads(pending_file.read_text(encoding="utf-8"))
                    persisted_identity["expires_at"] = "2020-01-01T00:00:00+00:00"
                    pending_file.write_text(json.dumps(persisted_identity), encoding="utf-8")
                    retained_identity = request_json(base_url + "/api/identity/bitcoin", True)
                    assert retained_identity["node_id"] == node_metadata["node_id"], retained_identity
                    registry = EntityIdentityRegistry(home / ".node-core")
                    entity_record = registry.get_entity(local_verified["identity"]["entity_id"])
                    assert entity_record["identity_assurance"] == "declared", entity_record
                    assert entity_record["node_links"][0]["node_id"] == node_metadata["node_id"], entity_record
                    assert entity_record["node_links"][0]["status"] == "declared", entity_record
                    assert len(entity_record["evidence_references"]) == 2, entity_record
                    pending_text = pending_file.read_text(encoding="utf-8")
                    assert "signature_hex" in pending_text and "node_association" in pending_text
                    identity_post("/api/identity/bitcoin/cancel", {})
                    print("Local Bitcoin key derivation, one-time signature, no private-key persistence and cleanup: PASS")
                    print("Bitcoin entity to installed Ed25519 NODE ID association and local entity registry: PASS")
                    print("Bitcoin P2WPKH address derivation, one-time ECDSA challenge, public-only persistence and replay rejection: PASS")

                catalog_response = request_json(base_url + "/api/certificates", tls_expected)
                assert catalog_response["catalog_version"] == "1.0.0", catalog_response
                assert len(catalog_response["security_profiles"]) == 8, catalog_response
                assert all(not item["installable_certificate"] for item in catalog_response["security_profiles"])
                print("Read-only certificate catalog endpoint: PASS")

                commands = request_json(base_url + "/api/termux/commands", tls_expected)
                command_ids = {item["id"] for item in commands["commands"]}
                assert "working-directory" in command_ids, commands
                assert {"user-id", "home-files", "current-date", "storage-space", "running-processes", "android-release", "android-abi", "installed-packages"}.issubset(command_ids), command_ids
                assert all(item.get("category") for item in commands["commands"]), commands
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

                    # Exercise the installed Node Core launcher through the
                    # actual interactive PTY API, including input and output.
                    terminal_start = urllib.request.Request(
                        base_url + "/api/terminal/start",
                        data=b"{}",
                        headers={
                            "Content-Type": "application/json",
                            "Origin": base_url,
                            "X-Node-Core-Lobby-Token": config["token"],
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(terminal_start, timeout=3.0, context=context) as response:
                        terminal_started = json.loads(response.read().decode("utf-8"))
                    assert terminal_started["status"] == "started", terminal_started
                    terminal = terminal_started["terminal"]
                    session_id = terminal["session_id"]
                    assert terminal["command"] == '"$HOME/.node-core/bin/node-core"', terminal

                    def terminal_request(action, extra=None):
                        payload = {"session_id": session_id}
                        if extra:
                            payload.update(extra)
                        request = urllib.request.Request(
                            base_url + "/api/terminal/" + action,
                            data=json.dumps(payload).encode("utf-8"),
                            headers={
                                "Content-Type": "application/json",
                                "Origin": base_url,
                                "X-Node-Core-Lobby-Token": config["token"],
                            },
                            method="POST",
                        )
                        with urllib.request.urlopen(request, timeout=3.0, context=context) as response:
                            return json.loads(response.read().decode("utf-8"))["terminal"]

                    deadline = time.monotonic() + 5
                    terminal_result = terminal_request("output")
                    while time.monotonic() < deadline and "NODE_CORE_TEST_LAUNCHER_EXECUTED" not in terminal_result["output"]:
                        time.sleep(0.05)
                        terminal_result = terminal_request("output")
                    assert "NODE_CORE_TEST_LAUNCHER_EXECUTED" in terminal_result["output"], terminal_result

                    terminal_request("input", {"input": "NODE_CORE_TERMINAL_INPUT_OK\n"})
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        terminal_result = terminal_request("output")
                        if "NODE_CORE_TEST_INPUT:NODE_CORE_TERMINAL_INPUT_OK" in terminal_result["output"]:
                            break
                        time.sleep(0.05)
                    assert "NODE_CORE_TEST_INPUT:NODE_CORE_TERMINAL_INPUT_OK" in terminal_result["output"], terminal_result

                    terminal_request("input", {"input": "exit\n"})
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        terminal_result = terminal_request("output")
                        if terminal_result["status"] == "exited":
                            break
                        time.sleep(0.05)
                    assert terminal_result["status"] == "exited", terminal_result
                    terminal_request("close")
                    print("Installed Node Core launcher PTY execution, interactive input and output: PASS")

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

    # Deterministic unit coverage for GNU/Linux, Termux, WSL, architecture and prerequisites.
    with tempfile.TemporaryDirectory(prefix="node-core-host-profile-") as profile_temp:
        profile_root = pathlib.Path(profile_temp)
        os_release = profile_root / "os-release"
        os_release.write_text('NAME="Debian GNU/Linux"\nID=debian\nVERSION_ID="12"\nPRETTY_NAME="Debian GNU/Linux 12"\n', encoding="utf-8")
        common = dict(
            os_release_path=os_release,
            proc_version_path=profile_root / "missing-proc-version",
            cgroup_path=profile_root / "missing-cgroup",
            container_marker_paths=(),
            command_lookup=lambda name: "/usr/bin/" + name if name in {
                "bash","python3","tar","sha512sum","mkdir","cp","rm","mktemp","uname","awk",
                "realpath","stat","id","find","grep","sed","nohup","curl","apt-get","pkg"
            } else None,
            python_version=(3,12,1),
        )
        linux = detect_host_environment({"SHELL":"/bin/bash","TERM_PROGRAM":"GNOME Terminal"},system="Linux",machine="x86_64",kernel_release="6.1",**common)
        assert linux["profile"] == "gnu_linux" and linux["distribution"]["id"] == "debian"
        assert linux["terminal"]["emulator"] == "GNOME Terminal" and linux["preflight_status"] == "ready"
        termux = detect_host_environment({"TERMUX_VERSION":"0.118","PREFIX":"/data/data/com.termux/files/usr"},system="Linux",machine="aarch64",**common)
        assert termux["profile"] == "termux" and termux["package_manager"]["id"] == "pkg"
        wsl = detect_host_environment({"WSL_DISTRO_NAME":"Ubuntu"},system="Linux",machine="x86_64",kernel_release="microsoft WSL2",**common)
        assert wsl["environment_type"] == "wsl"
        unsupported = detect_host_environment({},system="Linux",machine="riscv64",**common)
        assert unsupported["preflight_status"] == "unsupported"
        incomplete = detect_host_environment({},system="Linux",machine="x86_64",command_lookup=lambda name:None,python_version=(3,12,1),**{k:v for k,v in common.items() if k!="command_lookup"})
        assert incomplete["preflight_status"] == "requires_preparation"
        print("GNU/Linux distribution, Termux, WSL, architecture and capability detection: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
