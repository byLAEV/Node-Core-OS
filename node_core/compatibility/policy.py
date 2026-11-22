"""Manifest loading and capability-based GNU/Linux compatibility decisions."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class CompatibilityManifestError(ValueError):
    """The compatibility manifest is absent, malformed or incomplete."""

def default_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "compatibility" / "manifest.json"

def load_manifest(path: str | Path | None = None) -> dict[str, Any]:
    manifest_path = Path(path) if path is not None else default_manifest_path()
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CompatibilityManifestError(f"Cannot read compatibility manifest: {manifest_path}: {exc}") from exc
    profiles = value.get("supported_environments") if isinstance(value, dict) else None
    if value.get("manifest_version") != 1 or not isinstance(profiles, dict) or "gnu_linux" not in profiles:
        raise CompatibilityManifestError("Manifest must define version 1 and a GNU/Linux profile.")
    if "termux" in profiles or "android" in profiles:
        raise CompatibilityManifestError("Android and Termux profiles are forbidden for the Node Core OS runtime.")
    profile = profiles["gnu_linux"]
    if not isinstance(profile, dict) or not profile.get("architectures") or not isinstance(profile.get("required_commands"), list):
        raise CompatibilityManifestError("Invalid GNU/Linux compatibility profile.")
    if not isinstance(value.get("minimum_python"), str):
        raise CompatibilityManifestError("Manifest minimum_python must be a string.")
    return value

def _version_pair(value: str) -> tuple[int, int]:
    try:
        major, minor, *_ = value.split(".")
        return int(major), int(minor)
    except (ValueError, TypeError) as exc:
        raise CompatibilityManifestError(f"Invalid Python minimum version: {value!r}") from exc

def evaluate_environment(environment: dict[str, Any], manifest: dict[str, Any] | None = None, *, mode: str = "diagnose") -> dict[str, Any]:
    selected = manifest if manifest is not None else load_manifest()
    if mode not in {"diagnose", "prepare", "install", "update", "runtime"}:
        raise ValueError(f"Unsupported compatibility mode: {mode}")
    target, os_info = environment["target"], environment["os"]
    family, architecture = target["family"], target["architecture"]
    reasons: list[str] = []
    actions: list[str] = []
    warnings: list[str] = []
    missing: list[str] = []
    if os_info["system"] != "Linux":
        reasons.append("Node Core OS runtime requires GNU/Linux; Android is supported only through Lindesk.")
    elif family != "gnu_linux":
        reasons.append("This environment is not a supported GNU/Linux runtime (Android/Termux is excluded).")
    else:
        profile = selected["supported_environments"]["gnu_linux"]
        if architecture not in profile["architectures"]:
            reasons.append(f"Unsupported GNU/Linux architecture: {architecture}.")
        minimum = _version_pair(selected["minimum_python"])
        if tuple(environment["python"]["version"][:2]) < minimum:
            missing.append("Python >= " + selected["minimum_python"])
            actions.append("Install or select Python " + selected["minimum_python"] + " or newer.")
        for command in profile["required_commands"]:
            if not environment["commands"].get(command, False):
                missing.append(command)
        alternatives = profile.get("download_commands_any_of", [])
        if alternatives and not any(environment["commands"].get(item, False) for item in alternatives):
            missing.append("one of: " + " or ".join(alternatives))
        if missing:
            actions.append("Prepare only the listed dependencies; system package managers are not invoked automatically.")
        if not environment["terminal"]["interactive"]:
            warnings.append("No interactive TTY detected; menus require an interactive terminal.")
        if environment["terminal"]["term"].lower() == "dumb":
            warnings.append("TERM=dumb: use plain text without ANSI sequences.")
        if not environment["capabilities"]["systemd_user"]:
            warnings.append("systemd --user unavailable; use manual service lifecycle.")
        if os_info["id"] == "alpine":
            warnings.append("Alpine/musl is capability-checked and requires separate E2E evidence.")
    unsupported=bool(reasons)
    status="unsupported" if unsupported else ("requires_preparation" if missing else "ready")
    if status=="ready": actions.insert(0,"Environment meets the declared GNU/Linux capability requirements.")
    if status=="unsupported": actions.insert(0,"Stop before installation or update mutation; use a supported GNU/Linux host.")
    return {"compatibility_contract":selected.get("contract_id","NCTCL"),"mode":mode,"status":status,
      "profile":"gnu_linux" if family=="gnu_linux" and not unsupported else "unsupported",
      "validation_scope":"capability profile match; not proof of successful installation on this distro or architecture",
      "environment":environment,"missing_requirements":sorted(set(missing)),"reasons":reasons,"warnings":warnings,
      "recommended_actions":list(dict.fromkeys(actions)),"interactive_menu_available":bool(environment["terminal"]["interactive"]),
      "systemd_user_available":bool(environment["capabilities"]["systemd_user"]),
      "exit_code":3 if unsupported else (2 if missing else 0)}

def render_report(result: dict[str, Any]) -> str:
    labels={"ready":"READY BY CAPABILITIES","requires_preparation":"PREPARATION REQUIRED","unsupported":"UNSUPPORTED"}
    env=result["environment"]
    lines=["Node Core OS byLAEV — GNU/Linux Compatibility Preflight",f"Result: {labels[result['status']]}",
      f"Profile: {result['profile']}",f"System: {env['os']['pretty_name']} ({env['os']['id']})",
      f"Architecture: {env['target']['architecture']}",f"Python: {env['python']['version_string']}",
      f"Terminal: {env['terminal']['program']} / TERM={env['terminal']['term']}",
      f"Interactive TTY: {'yes' if env['terminal']['interactive'] else 'no'}",
      f"systemd --user: {'available' if env['capabilities']['systemd_user'] else 'not detected'}",
      f"Kubo CLI: {'available' if env['capabilities']['kubo_cli'] else 'not detected'}"]
    if result["missing_requirements"]: lines.append("Missing requirements: "+", ".join(result["missing_requirements"]))
    lines.extend("Blocker: "+x for x in result["reasons"])
    lines.extend("Warning: "+x for x in result["warnings"])
    lines.extend("Action: "+x for x in result["recommended_actions"])
    lines.append("Scope: "+result["validation_scope"])
    return "\n".join(lines)
