"""Manifest loading and capability-based compatibility decisions."""
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
    if not isinstance(value, dict) or value.get("manifest_version") != 1:
        raise CompatibilityManifestError("Unsupported compatibility manifest version.")
    profiles = value.get("supported_environments")
    if not isinstance(profiles, dict) or not {"gnu_linux", "termux"}.issubset(profiles):
        raise CompatibilityManifestError("Manifest must define GNU/Linux and Termux profiles.")
    for name in ("gnu_linux", "termux"):
        profile = profiles[name]
        if not isinstance(profile, dict):
            raise CompatibilityManifestError(f"Invalid profile: {name}")
        if not isinstance(profile.get("architectures"), list) or not profile["architectures"]:
            raise CompatibilityManifestError(f"Profile {name} has no architecture list.")
        if not isinstance(profile.get("required_commands"), list):
            raise CompatibilityManifestError(f"Profile {name} has no command list.")
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

    if os_info["system"] != "Linux" and not (os_info["system"] == "Android" and family == "termux"):
        reasons.append("Node Core OS requiere GNU/Linux o un entorno Termux identificado.")
    elif family not in {"gnu_linux", "termux"}:
        reasons.append("El entorno Linux no pudo clasificarse como GNU/Linux o Termux.")
    else:
        profile = selected["supported_environments"][family]
        if architecture not in profile["architectures"]:
            reasons.append(f"Arquitectura no soportada para {family}: {architecture}.")
        if family == "termux" and not environment["commands"].get("pkg", False):
            missing.append("pkg")
            actions.append("Verifica que el gestor nativo pkg de Termux esté disponible en PATH.")
        minimum = _version_pair(selected["minimum_python"])
        python_version = tuple(environment["python"]["version"][:2])
        if python_version < minimum:
            missing.append("Python >= " + selected["minimum_python"])
            actions.append("Selecciona Python " + selected["minimum_python"] + " o superior.")
        for command in profile["required_commands"]:
            if not environment["commands"].get(command, False):
                missing.append(command)
        alternatives = profile.get("download_commands_any_of", [])
        if alternatives and not any(environment["commands"].get(item, False) for item in alternatives):
            missing.append("uno de: " + " o ".join(alternatives))
        if missing:
            actions.append("Prepara solamente las dependencias listadas. En GNU/Linux no se ejecutan gestores de paquetes del sistema.")
        if not environment["terminal"]["interactive"]:
            warnings.append("No se detectó una TTY interactiva; los menús requieren terminal interactiva.")
        if environment["terminal"]["term"].lower() == "dumb":
            warnings.append("TERM=dumb: se debe usar salida de texto sin secuencias ANSI.")
        if not environment["capabilities"]["systemd_user"]:
            warnings.append("systemd --user no está disponible; se utilizará el ciclo manual de servicios.")
        if family == "gnu_linux" and os_info["id"] == "alpine":
            warnings.append("Alpine/musl se evalúa por capacidades; requiere evidencia E2E específica.")

    unsupported = bool(reasons)
    status = "unsupported" if unsupported else ("requires_preparation" if missing else "ready")
    if status == "ready":
        actions.insert(0, "El entorno satisface los requisitos declarados del perfil.")
    if status == "unsupported":
        actions.insert(0, "No ejecutar el instalador hasta declarar y probar un perfil compatible.")
    return {
        "compatibility_contract": selected.get("contract_id", "NCTCL"),
        "mode": mode, "status": status,
        "profile": family if family in {"gnu_linux", "termux"} else "unsupported",
        "validation_scope": "coincidencia de perfil y capacidades; no equivale a una prueba real de instalación en esta distribución, arquitectura o emulador",
        "environment": environment,
        "missing_requirements": sorted(set(missing)), "reasons": reasons, "warnings": warnings,
        "recommended_actions": list(dict.fromkeys(actions)),
        "interactive_menu_available": bool(environment["terminal"]["interactive"]),
        "systemd_user_available": bool(environment["capabilities"]["systemd_user"]),
        "exit_code": 3 if unsupported else (2 if missing else 0),
    }


def render_report(result: dict[str, Any]) -> str:
    labels = {"ready":"LISTO POR CAPACIDADES","requires_preparation":"REQUIERE PREPARACIÓN","unsupported":"NO SOPORTADO"}
    env = result["environment"]
    lines = [
        "Node Core OS byLAEV — Terminal Compatibility Preflight",
        f"Resultado: {labels[result['status']]}",
        f"Perfil: {result['profile']}",
        f"Sistema: {env['os']['pretty_name']} ({env['os']['id']})",
        f"Arquitectura: {env['target']['architecture']}",
        f"Entorno binario: {env['target']['libc']['name']} {env['target']['libc']['version']}",
        f"Python: {env['python']['version_string']} ({env['python']['implementation']})",
        f"Shell del instalador: {env['shell']['active']}",
        f"Terminal: {env['terminal']['program']} / TERM={env['terminal']['term']}",
        f"TTY interactiva: {'sí' if env['terminal']['interactive'] else 'no'}",
        f"systemd --user: {'disponible' if env['capabilities']['systemd_user'] else 'no detectado'}",
        f"Kubo CLI: {'disponible' if env['capabilities']['kubo_cli'] else 'no detectado'}",
    ]
    if result["missing_requirements"]:
        lines.append("Requisitos faltantes: " + ", ".join(result["missing_requirements"]))
    lines.extend("Bloqueo: " + item for item in result["reasons"])
    lines.extend("Aviso: " + item for item in result["warnings"])
    lines.extend("Acción: " + item for item in result["recommended_actions"])
    lines.append("Alcance: " + result["validation_scope"])
    return "\n".join(lines)
