#!/usr/bin/env python3
"""Read-only system inventory and local Lobby server for native Termux."""
from __future__ import annotations
import argparse, datetime as dt, json, os, platform, re, shutil, socket, ssl, subprocess, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOME = Path.home()
STATE = HOME / ".node-core" / "lobby"
CONFIG = STATE / "server.json"
CERT = STATE / "localhost.crt"
KEY = STATE / "localhost.key"
WEB = Path(__file__).resolve().parent / "web"
PACKAGE_LIMIT = 400
TREE_LIMIT = 180
SENSITIVE = re.compile(r"(?:^\.ssh$|^\.gnupg$|^keys?$|private|secret|credential|wallet|token|identity|keystore|\.pem$|\.key$|id_ed25519|id_rsa)", re.I)
SKIP_DIRS = {".git", "__pycache__", ".cache", "node_modules", ".venv", "venv"}

def run_command(args, timeout=3.0):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return {"returncode": r.returncode, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"returncode": 127, "stdout": "", "stderr": str(exc)}

def command_info(name, version_args=None):
    path = shutil.which(name)
    if not path:
        return {"available": False, "path": None, "version": None}
    version = None
    if version_args:
        r = run_command([path, *version_args], 2.0)
        text = r["stdout"] or r["stderr"]
        if text:
            version = text.splitlines()[0][:180]
    return {"available": True, "path": path, "version": version}

def termux_info():
    prefix = os.environ.get("PREFIX", "")
    marker = bool(os.environ.get("TERMUX_VERSION")) and prefix.startswith("/data/data/com.termux")
    release = run_command(["getprop", "ro.build.version.release"], 1.5)["stdout"]
    sdk = run_command(["getprop", "ro.build.version.sdk"], 1.5)["stdout"]
    shell = os.environ.get("SHELL", "")
    return {
        "platform": "Android / Termux" if marker else platform.platform(),
        "is_termux": marker, "android_release": release or None, "android_sdk": sdk or None,
        "kernel": platform.release(), "machine": platform.machine(),
        "architecture": platform.architecture()[0], "python": sys.version.split()[0],
        "python_executable": sys.executable, "shell": Path(shell).name if shell else None,
        "shell_path": shell or None, "term": os.environ.get("TERM"),
        "termux_version": os.environ.get("TERMUX_VERSION"), "prefix": prefix or None,
        "home": str(HOME), "uid": os.getuid() if hasattr(os, "getuid") else None
    }

def detect_node_core():
    app = HOME / ".node-core" / "app"
    data = HOME / ".node-core"
    launcher = data / "bin" / "node-core"
    version_file = app / "VERSION"
    try:
        version = version_file.read_text(encoding="utf-8").strip()[:80] if version_file.is_file() else None
    except OSError:
        version = None
    app_exists, launcher_exists = app.is_dir(), launcher.is_file()
    installed = app_exists and bool(version) and launcher_exists
    partial = (app_exists or launcher_exists) and not installed
    checkouts = []
    for candidate in (HOME / "Node-Core-OS", HOME / "Node-Core-OS-termux-lobby"):
        if candidate.is_dir():
            checkouts.append({
                "path": str(candidate), "is_git_repository": (candidate / ".git").exists(),
                "has_node_core_source": (candidate / "node_core").is_dir() or (candidate / "installer" / "install.sh").is_file(),
                "is_lobby_checkout": (candidate / "compatibility" / "termux" / "lobby").is_dir()
            })
    layout = {}
    for name in ("app", "bin", "config", "storage", "ipfs", "logs", "runtime", "services", "lobby"):
        p = data / name
        layout[name] = {"exists": p.exists(), "is_directory": p.is_dir()}
    return {
        "status": "installed" if installed else ("partial_or_residual" if partial else "not_installed"),
        "installed": installed, "partial_or_residual": partial, "data_directory": str(data),
        "version": version, "application_directory_exists": app_exists,
        "version_file_exists": version_file.is_file(), "launcher_exists": launcher_exists,
        "launcher_path": str(launcher), "layout": layout, "repository_checkouts": checkouts
    }

def package_inventory():
    fmt = "$" + "{binary:Package}\t" + "$" + "{Version}\n"
    r = run_command(["dpkg-query", "-W", "-f=" + fmt], 12.0)
    source, lines = "dpkg-query", r["stdout"].splitlines()
    if r["returncode"] != 0 and not lines:
        source = "pkg list-installed"
        r = run_command(["pkg", "list-installed"], 15.0)
        lines = r["stdout"].splitlines()
    items = []
    for line in lines:
        if not line.strip():
            continue
        if source == "dpkg-query":
            parts = line.split("\t", 1)
            if len(parts) == 2:
                items.append({"name": parts[0], "version": parts[1]})
        else:
            m = re.match(r"^([A-Za-z0-9+_.:-]+)/(\S+)\s+\S+\s+(\S+)", line)
            if m:
                items.append({"name": m.group(1), "version": m.group(3)})
    items.sort(key=lambda x: x["name"].lower())
    return {"source": source, "total_detected": len(items), "limit": PACKAGE_LIMIT,
            "truncated": len(items) > PACKAGE_LIMIT, "packages": items[:PACKAGE_LIMIT],
            "error": r["stderr"][:300] if r["returncode"] != 0 else None}

def network_report():
    interfaces = []
    root = Path("/sys/class/net")
    try:
        for entry in sorted(root.iterdir(), key=lambda p: p.name):
            try:
                state = (entry / "operstate").read_text().strip()
            except OSError:
                state = "unknown"
            interfaces.append({"name": entry.name, "state": state})
    except OSError:
        pass
    nameservers = []
    try:
        for line in Path("/etc/resolv.conf").read_text(errors="replace").splitlines():
            m = re.match(r"\s*nameserver\s+(\S+)", line)
            if m and m.group(1) not in nameservers:
                nameservers.append(m.group(1))
    except OSError:
        pass
    resolved, dns_error = [], None
    try:
        answers = socket.getaddrinfo("github.com", 443, type=socket.SOCK_STREAM)
        resolved = sorted({x[4][0] for x in answers})[:8]
    except OSError as exc:
        dns_error = str(exc)[:240]
    tcp_ok, tcp_error = False, None
    try:
        with socket.create_connection(("github.com", 443), timeout=3.0):
            tcp_ok = True
    except OSError as exc:
        tcp_error = str(exc)[:240]
    local = []
    for name, port in (("Kubo RPC API", 5001), ("Kubo Gateway", 8080), ("Node Core Lobby", 8765)):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                opened = True
        except OSError:
            opened = False
        local.append({"name": name, "host": "127.0.0.1", "port": port, "accepting_connections": opened})
    proxy = any(os.environ.get(k) for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"))
    return {
        "interfaces": interfaces,
        "dns": {"nameservers": nameservers, "github_com_resolves": bool(resolved), "resolved_addresses": resolved, "error": dns_error},
        "internet_tcp": {"github_com_443_reachable": tcp_ok, "error": tcp_error},
        "local_services": local, "proxy_configured": proxy, "proxy_values_withheld": True
    }

def tree_node(path, depth, counter):
    item = {"name": path.name or str(path), "type": "directory" if path.is_dir() else "file"}
    try:
        if path.is_symlink():
            return {"name": path.name, "type": "symlink", "note": "Not followed"}
        if path.is_file():
            return item
        if depth <= 0:
            item["note"] = "Depth limit reached"
            return item
        if path.name.lower() in ("storage", "ipfs"):
            item["note"] = "Contents not traversed; may contain user data"
            try:
                item["child_directories"] = sum(1 for p in path.iterdir() if p.is_dir() and not p.is_symlink())
            except OSError:
                item["child_directories"] = None
            return item
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))
        children = []
        for e in entries:
            if counter[0] >= TREE_LIMIT:
                item["truncated"] = True
                break
            if e.name in SKIP_DIRS or SENSITIVE.search(e.name):
                continue
            counter[0] += 1
            children.append(tree_node(Path(e.path), depth - 1, counter))
        item["children"] = children
    except OSError as exc:
        item["error"] = str(exc)[:160]
    return item

def directory_report():
    targets = [
        ("Termux HOME", HOME, 2), ("Node Core OS data", HOME / ".node-core", 4),
        ("Node Core OS Lobby checkout", HOME / "Node-Core-OS-termux-lobby", 3),
        ("Node Core OS checkout", HOME / "Node-Core-OS", 3),
        ("Termux PREFIX top level", Path(os.environ.get("PREFIX", "/nonexistent")), 1),
        ("Termux shortcuts", HOME / ".shortcuts", 2)
    ]
    output = []
    for label, path, depth in targets:
        if path.is_dir():
            output.append({"label": label, "path": str(path), "exists": True,
                           "tree": tree_node(path, depth, [0])})
        else:
            output.append({"label": label, "path": str(path), "exists": False, "tree": None})
    return {
        "targets": output,
        "policy": "Names and directory structure only. No file contents are read. Symlinks and sensitive paths are not traversed; storage and IPFS contents are not traversed."
    }

def system_tools():
    specs = {
        "bash": ["--version"], "python": ["--version"], "git": ["--version"],
        "curl": ["--version"], "openssl": ["version"], "pkg": None,
        "dpkg-query": None, "ip": ["-Version"], "termux-open-url": None,
        "termux-wake-lock": None, "node": ["--version"], "ipfs": ["--version"], "kubo": ["version"]
    }
    return {name: command_info(name, args) for name, args in specs.items()}

def diagnostics():
    info, node = termux_info(), detect_node_core()
    tools, packages, network, directories = system_tools(), package_inventory(), network_report(), directory_report()
    checks = []
    def add(name, ok, detail, severity="required"):
        checks.append({"name": name, "ok": bool(ok), "detail": str(detail), "severity": severity})
    add("Native Termux markers", info["is_termux"], info["platform"])
    add("Supported architecture", info["machine"] in ("aarch64", "arm64"), info["machine"])
    add("Python >= 3.10", sys.version_info >= (3, 10), sys.version.split()[0])
    add("Termux package manager", tools["pkg"]["available"], tools["pkg"]["path"] or "Not found")
    add("Git", tools["git"]["available"], tools["git"]["path"] or "Not found")
    add("curl", tools["curl"]["available"], tools["curl"]["path"] or "Not found")
    add("OpenSSL executable", tools["openssl"]["available"], tools["openssl"]["path"] or "Install package openssl-tool", "recommended")
    add("DNS resolution", network["dns"]["github_com_resolves"], network["dns"]["error"] or ", ".join(network["dns"]["resolved_addresses"]), "recommended")
    add("Outbound TCP 443", network["internet_tcp"]["github_com_443_reachable"], network["internet_tcp"]["error"] or "github.com:443 reachable", "recommended")
    add("Node Core OS installation", node["installed"], node["status"] + " · " + node["data_directory"], "informational")
    add("Kubo CLI", tools["ipfs"]["available"] or tools["kubo"]["available"], tools["ipfs"]["path"] or tools["kubo"]["path"] or "Not detected", "recommended")
    try:
        free_mb = shutil.disk_usage(HOME).free // (1024 * 1024)
        add("Available storage", free_mb >= 200, str(free_mb) + " MB free (preliminary threshold: 200 MB)")
    except OSError as exc:
        add("Available storage", False, exc)
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "environment": info, "node_core": node, "tools": tools, "packages": packages,
        "network": network, "directories": directories, "checks": checks,
        "summary": {
            "passed": sum(1 for x in checks if x["ok"]),
            "failed_required": sum(1 for x in checks if not x["ok"] and x["severity"] == "required"),
            "warnings": sum(1 for x in checks if not x["ok"] and x["severity"] == "recommended"),
            "total": len(checks)
        },
        "privacy": {
            "read_only": True, "file_contents_read": False, "proxy_values_exposed": False,
            "sensitive_directories_traversed": False, "package_limit": PACKAGE_LIMIT,
            "directory_entry_limit_per_root": TREE_LIMIT
        }
    }

def load_config():
    STATE.mkdir(parents=True, exist_ok=True)
    if CONFIG.exists():
        data = json.loads(CONFIG.read_text())
        if data.get("bind") != "127.0.0.1" or not isinstance(data.get("port"), int):
            raise RuntimeError("Unsafe or invalid Lobby configuration")
        return data
    import secrets
    data = {"bind": "127.0.0.1", "port": 8765, "token": secrets.token_urlsafe(32), "https": True}
    CONFIG.write_text(json.dumps(data, indent=2) + "\n")
    CONFIG.chmod(0o600)
    return data

def ensure_certificate():
    if CERT.exists() and KEY.exists():
        return True
    openssl = shutil.which("openssl")
    if not openssl:
        return False
    result = subprocess.run([
        openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(KEY), "-out", str(CERT), "-days", "365",
        "-subj", "/CN=localhost",
        "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if result.returncode == 0:
        KEY.chmod(0o600)
        CERT.chmod(0o600)
        return True
    return False

class Handler(BaseHTTPRequestHandler):
    server_version = "NodeCoreLobby/0.3"
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self.send_json({"status": "ok", "transport": "https" if self.server.is_https else "http"})
        elif path in ("/api/diagnostics", "/api/report"):
            self.send_json(diagnostics())
        elif path == "/api/status":
            self.send_json({
                "status": "running", "transport": "https" if self.server.is_https else "http",
                "environment": termux_info(), "node_core": detect_node_core()
            })
        elif path in ("/", "/index.html"):
            self.send_file(WEB / "index.html", "text/html; charset=utf-8")
        elif path == "/manifest.webmanifest":
            self.send_file(WEB / "manifest.webmanifest", "application/manifest+json")
        elif path == "/icon.svg":
            self.send_file(WEB / "icon.svg", "image/svg+xml")
        else:
            self.send_error(404)
    def send_file(self, path, content_type):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)
    def send_json(self, obj):
        data = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, fmt, *args):
        print("[lobby] " + fmt % args, flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    cfg = load_config()
    if args.check:
        print(json.dumps({
            "config": str(CONFIG), "bind": cfg["bind"], "port": cfg["port"],
            "https": cfg["https"], "environment": termux_info()
        }, indent=2))
        return 0
    httpd = ThreadingHTTPServer((cfg["bind"], cfg["port"]), Handler)
    httpd.daemon_threads = True
    use_https = bool(cfg.get("https")) and ensure_certificate()
    if use_https:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(CERT), str(KEY))
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    httpd.is_https = use_https
    scheme = "https" if use_https else "http"
    print(f"NODE CORE OS LOBBY listening on {scheme}://127.0.0.1:{cfg['port']}/", flush=True)
    print("Read-only inventory API. Loopback only; no LAN exposure.", flush=True)
    try:
        httpd.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
