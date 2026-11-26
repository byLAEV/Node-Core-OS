"""Permission-aware, non-root network diagnostics for Node Core OS.

The collector is intentionally read-only. It never changes interfaces, routes, DNS,
firewall rules, Android settings, or Kubo configuration. Restricted /proc files are
reported as unavailable rather than treated as proof that networking is down.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
from typing import Any


def _read_text(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8").strip(), None
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _interfaces() -> list[dict[str, Any]]:
    root = Path("/sys/class/net")
    try:
        names = sorted(entry.name for entry in root.iterdir())
    except OSError:
        return []
    result = []
    for name in names:
        item: dict[str, Any] = {"name": name}
        state, _ = _read_text(root / name / "operstate")
        mtu, _ = _read_text(root / name / "mtu")
        item["state"] = state or "unknown"
        try:
            item["mtu"] = int(mtu) if mtu else None
        except ValueError:
            item["mtu"] = None
        result.append(item)
    return result


def _default_route() -> dict[str, Any]:
    """Try the normal unprivileged ip command, then the proc route table."""
    ip_command = shutil.which("ip")
    if ip_command:
        try:
            completed = subprocess.run(
                [ip_command, "route", "show", "default"],
                capture_output=True, text=True, timeout=2, check=False,
            )
            if completed.returncode == 0:
                line = next((row.strip() for row in completed.stdout.splitlines() if row.strip()), "")
                if line:
                    fields = line.split()
                    route: dict[str, Any] = {"available": True, "source": "ip route", "raw": line}
                    if "via" in fields:
                        route["gateway"] = fields[fields.index("via") + 1]
                    if "dev" in fields:
                        route["interface"] = fields[fields.index("dev") + 1]
                    return route
        except (OSError, subprocess.TimeoutExpired):
            pass

    raw, error = _read_text(Path("/proc/net/route"))
    if raw is not None:
        for line in raw.splitlines()[1:]:
            fields = line.split()
            if len(fields) >= 3 and fields[1] == "00000000":
                try:
                    gateway_int = int(fields[2], 16)
                    gateway = socket.inet_ntoa(gateway_int.to_bytes(4, byteorder="little"))
                except (ValueError, OSError, OverflowError):
                    gateway = None
                return {
                    "available": True, "source": "/proc/net/route",
                    "interface": fields[0], "gateway": gateway, "raw": line,
                }
        return {"available": False, "source": "/proc/net/route", "detail": "No default route found."}
    return {"available": False, "source": "/proc/net/route", "detail": error or "Route table unavailable."}


def _dns_probe() -> dict[str, Any]:
    started = time.monotonic()
    try:
        addresses = sorted({
            item[4][0] for item in socket.getaddrinfo(
                "example.com", 443, type=socket.SOCK_STREAM
            )
        })
        return {
            "status": "PASS", "host": "example.com",
            "addresses": addresses[:8],
            "latency_ms": round((time.monotonic() - started) * 1000, 1),
        }
    except (OSError, socket.gaierror) as exc:
        return {"status": "FAIL", "host": "example.com", "detail": str(exc)}


def _tcp_probe(host: str, port: int = 443, timeout: float = 1.5) -> dict[str, Any]:
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {
                "status": "PASS", "target": f"{host}:{port}",
                "latency_ms": round((time.monotonic() - started) * 1000, 1),
            }
    except OSError as exc:
        return {"status": "FAIL", "target": f"{host}:{port}", "detail": str(exc)}


def collect_network_diagnostics(*, probe_external: bool = True) -> dict[str, Any]:
    """Return a best-effort snapshot that works without root and tolerates Android limits."""
    interfaces = _interfaces()
    route = _default_route()
    dns = _dns_probe() if probe_external else {"status": "NOT_CHECKED"}
    connectivity = (
        [_tcp_probe("1.1.1.1"), _tcp_probe("8.8.8.8")]
        if probe_external else []
    )
    proc_files: dict[str, dict[str, Any]] = {}
    for name in ("dev", "route", "tcp", "tcp6", "udp", "udp6", "arp"):
        value, error = _read_text(Path("/proc/net") / name)
        proc_files[name] = {
            "available": value is not None,
            "detail": error,
            "line_count": len(value.splitlines()) if value is not None else None,
        }
    try:
        android_dns = sorted({
            value for key, value in os.environ.items()
            if key.upper().startswith("ANDROID_DNS") and value.strip()
        })
    except Exception:
        android_dns = []
    return {
        "interfaces": interfaces,
        "interface_count": len(interfaces),
        "default_route": route,
        "dns_resolution": dns,
        "tcp_connectivity": connectivity,
        "android_dns_environment": android_dns,
        "proc_net": proc_files,
        "limitations": [
            "Android/Termux may restrict /proc/net and route-table visibility without root.",
            "A successful TCP probe confirms reachability to that endpoint only, not native Node Core P2P reachability.",
            "A failed ICMP ping is not used as proof of Internet failure.",
        ],
    }
