"""Read-only detection of Linux, terminal, shell and runtime capabilities."""
from __future__ import annotations
import os
from pathlib import Path
import platform
import shlex
import shutil
import sys
from typing import Callable, Mapping


def parse_os_release(text: str) -> dict[str, str]:
    """Parse os-release key/value lines without executing or sourcing the file."""
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "").isalnum():
            continue
        try:
            parts = shlex.split(raw_value.strip(), posix=True)
            value = parts[0] if len(parts) == 1 else raw_value.strip().strip(chr(34)).strip(chr(39))
        except ValueError:
            value = raw_value.strip().strip(chr(34)).strip(chr(39))
        result[key] = value
    return result


def _read_os_release() -> dict[str, str]:
    for candidate in (Path("/etc/os-release"), Path("/usr/lib/os-release")):
        try:
            return parse_os_release(candidate.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            pass
    return {}


def normalize_architecture(machine: str) -> str:
    value = machine.strip().lower()
    aliases = {"amd64": "x86_64", "x64": "x86_64", "arm64": "aarch64", "armv8": "aarch64"}
    return aliases.get(value, value or "unknown")


def _terminal_program(env: Mapping[str, str]) -> str:
    if env.get("TERM_PROGRAM"):
        return env["TERM_PROGRAM"]
    if env.get("KONSOLE_VERSION"):
        return "Konsole"
    if env.get("GNOME_TERMINAL_SERVICE"):
        return "GNOME Terminal"
    if env.get("XTERM_VERSION"):
        return "xterm-compatible"
    if env.get("TMUX"):
        return "tmux"
    if env.get("STY"):
        return "screen"
    return "unknown"


def detect_environment(
    *,
    env: Mapping[str, str] | None = None,
    system: str | None = None,
    kernel_system: str | None = None,
    machine: str | None = None,
    python_version: tuple[int, int, int] | None = None,
    terminal_isatty: bool | None = None,
    os_release_text: str | None = None,
    command_lookup: Callable[[str], str | None] | None = None,
    current_uid: int | None = None,
    libc_info: tuple[str, str] | None = None,
) -> dict:
    env_values = dict(os.environ if env is None else env)
    active_system = system if system is not None else platform.system()
    if kernel_system is not None:
        active_kernel_system = kernel_system
    else:
        try:
            active_kernel_system = os.uname().sysname
        except (AttributeError, OSError):
            active_kernel_system = active_system
    active_machine = machine if machine is not None else platform.machine()
    active_python = python_version if python_version is not None else tuple(sys.version_info[:3])
    lookup = command_lookup or (lambda name: shutil.which(name, path=env_values.get("PATH")))
    os_release = parse_os_release(os_release_text) if os_release_text is not None else _read_os_release()
    prefix = env_values.get("PREFIX", "")
    termux_marker = bool(env_values.get("TERMUX_VERSION") and prefix)
    # Android Python may report platform.system() == "Android" even though
    # Termux runs on the Linux kernel. Detect the kernel independently and
    # require Termux-specific markers; pkg remains a separately checked
    # capability so a missing package manager is reported as preparation.
    is_termux = active_kernel_system == "Linux" and termux_marker
    effective_system = "Linux" if is_termux else active_system
    family = "termux" if is_termux else ("gnu_linux" if effective_system == "Linux" else "unsupported")
    architecture = normalize_architecture(active_machine)

    term = env_values.get("TERM", "")
    if terminal_isatty is None:
        try:
            is_tty = bool(sys.stdin.isatty() and sys.stdout.isatty())
        except (AttributeError, OSError):
            is_tty = False
    else:
        is_tty = bool(terminal_isatty)
    interactive = is_tty and term.lower() != "dumb"
    ansi = is_tty and bool(term) and term.lower() != "dumb"

    libc_name, libc_version = libc_info if libc_info is not None else platform.libc_ver()
    distro_id = os_release.get("ID", "").lower()
    if not libc_name and distro_id == "alpine":
        libc_name = "musl"
    libc_name = libc_name or "unknown"

    uid = current_uid
    if uid is None:
        uid = os.getuid() if hasattr(os, "getuid") else -1
    runtime_dir = env_values.get("XDG_RUNTIME_DIR", f"/run/user/{uid}" if uid >= 0 else "")
    bus_path = Path(runtime_dir) / "bus" if runtime_dir else None
    systemd_user = bool(
        lookup("systemctl")
        and ((bus_path is not None and bus_path.exists())
             or env_values.get("DBUS_SESSION_BUS_ADDRESS", "").startswith("unix:"))
    )

    command_names = (
        "bash", "python3", "tar", "sha512sum", "mkdir", "cp", "rm", "mktemp",
        "uname", "awk", "realpath", "stat", "id", "find", "grep", "sed", "nohup",
    )
    commands = {name: bool(lookup(name)) for name in command_names}
    commands.update({
        "curl": bool(lookup("curl")), "wget": bool(lookup("wget")),
        "pkg": bool(lookup("pkg")), "ipfs": bool(lookup("ipfs")),
    })
    package_managers = {
        name: bool(lookup(name))
        for name in ("apt-get", "apt", "dnf", "yum", "pacman", "zypper", "apk", "pkg")
    }
    active_shell = (
        env_values.get("NODE_CORE_ACTIVE_SHELL")
        or ("bash" if env_values.get("BASH_VERSION") else "")
        or ("zsh" if env_values.get("ZSH_VERSION") else "")
        or ("fish" if env_values.get("FISH_VERSION") else "")
        or "unknown"
    )
    return {
        "os": {
            "system": effective_system, "name": os_release.get("NAME", "unknown"),
            "id": distro_id or ("termux" if is_termux else "unknown"),
            "id_like": os_release.get("ID_LIKE", "").lower().split(),
            "version_id": os_release.get("VERSION_ID", "unknown"),
            "pretty_name": os_release.get("PRETTY_NAME", os_release.get("NAME", "unknown")),
        },
        "target": {
            "family": family, "architecture": architecture,
            "libc": {"name": libc_name, "version": libc_version or "unknown"},
            "termux_prefix": prefix if is_termux else "",
        },
        "python": {
            "version": list(active_python),
            "version_string": ".".join(str(part) for part in active_python),
            "implementation": platform.python_implementation(), "executable": sys.executable,
        },
        "shell": {
            "active": active_shell, "declared_user_shell": env_values.get("SHELL", "unknown"),
            "installer_requires": "bash",
        },
        "terminal": {
            "term": term or "unknown", "program": _terminal_program(env_values),
            "is_tty": is_tty, "interactive": interactive, "ansi_color": ansi,
        },
        "commands": commands, "package_managers": package_managers,
        "capabilities": {
            "systemd_user": systemd_user, "kubo_cli": commands["ipfs"],
            "interactive_terminal": interactive, "ansi_color": ansi,
        },
    }
