"""Simple GitHub Pages and personal-node binding for the first functional phase.

This first version favors observable behavior over privacy: records are stored
as readable JSON in the local outbox and in the operator's GitHub repository.
Do not use real personal information until the privacy phase is implemented.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class GitHubBindingError(RuntimeError):
    """Raised when a GitHub repository cannot be bound or synchronized."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _login(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"(?!-)[A-Za-z0-9-]{1,39}(?<!-)", value):
        raise GitHubBindingError("GitHub username must contain 1-39 letters, digits or hyphens.")
    return value.lower()


def _repository(login: str, value: str) -> str:
    if not isinstance(value, str) or value.count("/") != 1:
        raise GitHubBindingError("Repository must use owner/repository format.")
    owner, name = value.split("/", 1)
    if owner.lower() != login or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", name):
        raise GitHubBindingError("Repository must belong to the configured GitHub account.")
    return owner + "/" + name


class GitHubNodeBinding:
    """Bind one GitHub Pages client repository to this node and append records."""

    SCHEMA = "node-core-os/github-node-binding/v1"

    def __init__(self, data_dir: Path, identity_store: Any) -> None:
        self.root = Path(data_dir).expanduser() / "identity" / "github-binding"
        self.binding_path = self.root / "binding.json"
        self.outbox = self.root / "outbox"
        self.identity_store = identity_store

    def configure(
        self,
        github_login: str,
        repository: str,
        pages_url: str | None = None,
        github_app_installation_id: str | None = None,
        node_api_url: str | None = None,
    ) -> dict[str, Any]:
        login = _login(github_login)
        repo = _repository(login, repository)
        repo_name = repo.split("/", 1)[1]
        expected_page = f"https://{login}.github.io/{repo_name}/"
        page = (pages_url or expected_page).strip()
        if page.rstrip("/") != expected_page.rstrip("/"):
            raise GitHubBindingError(f"GitHub Pages URL must be {expected_page}")
        identity = self.identity_store.initialize()
        installation = str(github_app_installation_id or "").strip() or None
        api_url = (node_api_url or "").strip().rstrip("/")
        if api_url:
            parsed_api = urlsplit(api_url)
            if parsed_api.scheme not in {"http", "https"} or not parsed_api.netloc or parsed_api.query or parsed_api.fragment:
                raise GitHubBindingError("Node API URL must be an absolute HTTP or HTTPS URL without query or fragment.")
        if installation and not installation.isdigit():
            raise GitHubBindingError("GitHub App installation ID must contain only digits.")
        self.root.mkdir(parents=True, exist_ok=True)
        self.outbox.mkdir(parents=True, exist_ok=True)
        value = {
            "schema": self.SCHEMA,
            "github_account": login,
            "repository_owner": login,
            "repository_name": repo_name,
            "repository": repo,
            "github_app_installation_id": installation,
            "github_pages_url": expected_page,
            "node_api_url": api_url,
            "node_id": identity["node_id"],
            "default_branch": "main",
            "binding_status": "configured",
            "created_at_utc": _now(),
        }
        self._write_json(self.binding_path, value)
        return value

    def status(self) -> dict[str, Any]:
        if not self.binding_path.is_file():
            return {"binding_status": "not_configured", "node_id": self.identity_store.initialize()["node_id"]}
        value = json.loads(self.binding_path.read_text(encoding="utf-8"))
        identity = self.identity_store.load()
        if value.get("node_id") != identity["node_id"]:
            raise GitHubBindingError("Saved GitHub binding belongs to a different node identity.")
        value["pending_records"] = len(list(self.outbox.glob("*.json"))) if self.outbox.exists() else 0
        return value

    def export_client_package(self, target_dir: Path) -> Path:
        """Copy the static Pages client and write this node's public configuration."""
        binding = self.status()
        if binding.get("binding_status") != "configured":
            raise GitHubBindingError("Configure the GitHub repository before exporting the client.")
        if not binding.get("node_api_url"):
            raise GitHubBindingError("Configure the public Node API URL before exporting the client.")
        source = Path(__file__).resolve().parents[1] / "client-template"
        if not source.is_dir():
            raise GitHubBindingError(f"Client template directory is missing: {source}")
        target = Path(target_dir).expanduser()
        if target.exists() and any(target.iterdir()):
            raise GitHubBindingError(f"Refusing to overwrite a non-empty client directory: {target}")
        if target.exists():
            target.rmdir()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
        client_config = {
            "schema": "node-core-os/github-pages-client/v1",
            "github_account": binding["github_account"],
            "repository": binding["repository"],
            "github_pages_url": binding["github_pages_url"],
            "node_id": binding["node_id"],
            "node_api_url": binding["node_api_url"],
            "client_version": "1.0.0",
        }
        self._write_json(target / "node-core-client.json", client_config)
        return target

    def add_record(self, fields: dict[str, Any]) -> dict[str, Any]:
        binding = self.status()
        if binding.get("binding_status") != "configured":
            raise GitHubBindingError("Configure the GitHub repository before receiving records.")
        if not isinstance(fields, dict) or not fields:
            raise GitHubBindingError("Record fields must be a non-empty JSON object.")
        record = {
            "schema": "node-core-os/github-page-record/v1",
            "record_id": str(uuid.uuid4()),
            "node_id": binding["node_id"],
            "github_account": binding["github_account"],
            "repository": binding["repository"],
            "source_pages_url": binding["github_pages_url"],
            "created_at_utc": _now(),
            "fields": fields,
            "sync_status": "pending",
        }
        self.outbox.mkdir(parents=True, exist_ok=True)
        self._write_json(self.outbox / (record["record_id"] + ".json"), record)
        return record

    def sync(self) -> dict[str, Any]:
        binding = self.status()
        if binding.get("binding_status") != "configured":
            raise GitHubBindingError("GitHub repository is not configured.")
        token = self._github_token(binding)
        repository = self._api("GET", f"/repos/{binding['repository']}", token)
        owner = (repository.get("owner") or {}).get("login", "")
        if owner.lower() != binding["github_account"]:
            raise GitHubBindingError("GitHub repository owner does not match the node binding.")
        branch = repository.get("default_branch") or "main"
        synced = 0
        pending = sorted(self.outbox.glob("*.json"))
        for path in pending:
            record = json.loads(path.read_text(encoding="utf-8"))
            record["sync_status"] = "synced"
            record["synced_at_utc"] = _now()
            created = datetime.fromisoformat(record["created_at_utc"])
            remote_path = f"records/{created:%Y}/{created:%m}/{record['record_id']}.json"
            body = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
            import base64
            payload = {
                "message": "node-core: add page record " + record["record_id"],
                "content": base64.b64encode(body.encode("utf-8")).decode("ascii"),
                "branch": branch,
            }
            self._api("PUT", f"/repos/{binding['repository']}/contents/{remote_path}", token, payload)
            self._write_json(path, record)
            path.unlink()
            synced += 1
        binding["default_branch"] = branch
        binding["last_sync_at_utc"] = _now()
        binding["last_sync_count"] = synced
        self._write_json(self.binding_path, binding)
        return {"repository": binding["repository"], "branch": branch, "synced": synced, "pending": 0}

    def _github_token(self, binding: dict[str, Any]) -> str:
        app_id = os.environ.get("NODE_CORE_GITHUB_APP_ID", "").strip()
        private_key = os.environ.get("NODE_CORE_GITHUB_APP_PRIVATE_KEY", "").strip()
        installation_id = str(binding.get("github_app_installation_id") or "").strip()
        if installation_id and app_id and private_key:
            from node_core.github_app_auth import GitHubAppAuth
            return GitHubAppAuth(self.root.parent.parent).installation_token(
                installation_id, binding["repository_name"], app_id, private_key
            )
        try:
            result = subprocess.run(
                ["gh", "auth", "token"], check=True, capture_output=True, text=True, timeout=10
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise GitHubBindingError("Run 'gh auth login' as the node owner before synchronizing.") from exc
        token = result.stdout.strip()
        if not token:
            raise GitHubBindingError("GitHub CLI did not return an authenticated token.")
        return token

    @staticmethod
    def _api(method: str, path: str, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            "https://api.github.com" + path,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + token,
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "Node-Core-OS-byLAEV",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise GitHubBindingError(f"GitHub API {method} failed for {path}: {exc}") from exc
        if not isinstance(result, dict):
            raise GitHubBindingError("GitHub API returned an unexpected response.")
        return result

    @staticmethod
    def _write_json(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
