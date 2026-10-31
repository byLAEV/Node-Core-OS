"""GitHub App device authorization and installation token helpers."""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


class GitHubAppError(RuntimeError):
    """GitHub authorization or App API operation failed."""


DEVICE_CODE_URL = "https://github.com/login/device/code"
OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
API_URL = "https://api.github.com"
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class GitHubAppAuth:
    """Link an operator account and create scoped installation tokens."""

    def __init__(self, data_dir: Path) -> None:
        self.root = Path(data_dir).expanduser() / "identity" / "github-binding"
        self.pending_path = self.root / "device-flow.json"
        self.operator_path = self.root / "operator-github.json"

    @staticmethod
    def _write(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        temporary.replace(path)

    def start_device_flow(self, client_id: str) -> dict[str, Any]:
        client_id = str(client_id or "").strip()
        if not client_id:
            raise GitHubAppError("Set NODE_CORE_GITHUB_APP_CLIENT_ID first.")
        data = self._post_form(DEVICE_CODE_URL, {
            "client_id": client_id,
            "scope": "offline_access",
        })
        required = ("device_code", "user_code", "verification_uri", "expires_in", "interval")
        if any(key not in data for key in required):
            raise GitHubAppError("GitHub returned an incomplete device authorization response.")
        now = time.time()
        state = {
            "client_id": client_id,
            "device_code": data["device_code"],
            "user_code": data["user_code"],
            "verification_uri": data["verification_uri"],
            "expires_at": now + int(data["expires_in"]),
            "interval": int(data["interval"]),
            "next_poll_at": now + int(data["interval"]),
        }
        self._write(self.pending_path, state)
        return {
            "state": "pending",
            "user_code": state["user_code"],
            "verification_uri": state["verification_uri"],
            "expires_in": int(data["expires_in"]),
            "interval": state["interval"],
        }

    def poll_device_flow(self, expected_login: str | None = None) -> dict[str, Any]:
        if not self.pending_path.is_file():
            raise GitHubAppError("No device authorization is pending.")
        state = json.loads(self.pending_path.read_text(encoding="utf-8"))
        now = time.time()
        if now >= float(state["expires_at"]):
            self.pending_path.unlink(missing_ok=True)
            return {"state": "expired"}
        if now < float(state["next_poll_at"]):
            return {"state": "pending", "wait_seconds": round(state["next_poll_at"] - now, 1)}

        data = self._post_form(OAUTH_TOKEN_URL, {
            "client_id": state["client_id"],
            "device_code": state["device_code"],
            "grant_type": DEVICE_GRANT,
        })
        error = data.get("error")
        if error in {"authorization_pending", "slow_down"}:
            if error == "slow_down":
                state["interval"] = int(state["interval"]) + 5
            state["next_poll_at"] = now + int(state["interval"])
            self._write(self.pending_path, state)
            return {"state": "pending", "wait_seconds": int(state["interval"])}
        if error:
            if error in {"access_denied", "expired_token", "incorrect_device_code"}:
                self.pending_path.unlink(missing_ok=True)
            raise GitHubAppError("GitHub device authorization failed: " + str(error))

        access_token = data.get("access_token")
        if not access_token:
            raise GitHubAppError("GitHub did not return an access token.")
        user = self._get_json(API_URL + "/user", str(access_token))
        login = str(user.get("login", "")).strip().lower()
        if not login:
            raise GitHubAppError("Could not determine the authorized GitHub account.")
        if expected_login and login != expected_login.strip().lower():
            raise GitHubAppError(
                f"Authorized account '{login}' does not match configured operator '{expected_login}'."
            )

        operator = {
            "github_login": login,
            "access_token": access_token,
            "refresh_token": data.get("refresh_token"),
            "expires_at": now + int(data.get("expires_in", 28800)),
            "refresh_token_expires_at": (
                now + int(data["refresh_token_expires_in"])
                if data.get("refresh_token_expires_in") else None
            ),
            "authorized_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        self._write(self.operator_path, operator)
        self.pending_path.unlink(missing_ok=True)
        return {
            "state": "authorized",
            "github_login": login,
            "expires_at_utc": datetime.fromtimestamp(operator["expires_at"], timezone.utc).isoformat(),
        }

    def operator_status(self) -> dict[str, Any]:
        if not self.operator_path.is_file():
            return {"authorized": False, "github_login": None}
        value = json.loads(self.operator_path.read_text(encoding="utf-8"))
        return {
            "authorized": bool(value.get("access_token")),
            "github_login": value.get("github_login"),
            "authorized_at_utc": value.get("authorized_at_utc"),
            "expires_at_utc": datetime.fromtimestamp(
                float(value.get("expires_at", 0)), timezone.utc
            ).isoformat(),
        }

    def installation_token(
        self,
        installation_id: str,
        repository_name: str,
        app_id: str,
        private_key_path: str | Path,
    ) -> str:
        if not str(installation_id).isdigit():
            raise GitHubAppError("GitHub App installation ID must be numeric.")
        key_path = Path(private_key_path).expanduser()
        if not key_path.is_file():
            raise GitHubAppError(f"GitHub App private key file not found: {key_path}")
        jwt_token = self._create_app_jwt(app_id, key_path)
        result = self._post_json(
            f"{API_URL}/app/installations/{installation_id}/access_tokens",
            jwt_token,
            {
                "repositories": [repository_name],
                "permissions": {"contents": "write"},
            },
        )
        if not result.get("token"):
            raise GitHubAppError("GitHub did not return an installation access token.")
        return str(result["token"])

    @staticmethod
    def _create_app_jwt(app_id: str, private_key_path: Path) -> str:
        if not app_id.strip():
            raise GitHubAppError("Set NODE_CORE_GITHUB_APP_ID first.")
        try:
            key = serialization.load_pem_private_key(private_key_path.read_bytes(), password=None)
            now = int(time.time())
            header = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
            payload = _b64url(json.dumps({
                "iat": now - 60,
                "exp": now + 540,
                "iss": app_id.strip(),
            }, separators=(",", ":")).encode())
            message = (header + "." + payload).encode("ascii")
            signature = key.sign(message, padding.PKCS1v15(), hashes.SHA256())
            return message.decode("ascii") + "." + _b64url(signature)
        except (OSError, ValueError, TypeError) as exc:
            raise GitHubAppError(f"Could not create GitHub App JWT: {exc}") from exc

    @staticmethod
    def _post_form(url: str, fields: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(fields).encode("utf-8"),
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Node-Core-OS-byLAEV",
            },
        )
        return GitHubAppAuth._open_json(request)

    @staticmethod
    def _get_json(url: str, token: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "Node-Core-OS-byLAEV",
        })
        return GitHubAppAuth._open_json(request)

    @staticmethod
    def _post_json(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + token,
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "Node-Core-OS-byLAEV",
            },
        )
        return GitHubAppAuth._open_json(request)

    @staticmethod
    def _open_json(request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                value = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8")
            except OSError:
                detail = str(exc)
            raise GitHubAppError(f"GitHub HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise GitHubAppError(f"GitHub request failed: {exc}") from exc
        if not isinstance(value, dict):
            raise GitHubAppError("GitHub returned an unexpected response.")
        return value
