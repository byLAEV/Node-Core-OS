#!/usr/bin/env python3
"""Read-only local Node Core OS Lobby server for Termux."""
from __future__ import annotations
import argparse, json, os, secrets, shutil, ssl, subprocess, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOME = Path.home()
STATE = HOME / ".node-core" / "lobby"
CONFIG = STATE / "server.json"
CERT = STATE / "localhost.crt"
KEY = STATE / "localhost.key"
WEB = Path(__file__).resolve().parent / "web"

def termux_info():
    is_termux = bool(os.environ.get("TERMUX_VERSION")) or os.environ.get("PREFIX", "").startswith("/data/data/com.termux")
    return {
        "platform": "Android / Termux" if is_termux else sys.platform,
        "is_termux": is_termux,
        "architecture": os.uname().machine,
        "python": sys.version.split()[0],
        "prefix": os.environ.get("PREFIX", "not detected"),
        "home": str(HOME),
        "node_core_installed": (HOME / ".node-core" / "app").is_dir(),
    }

def diagnostics():
    info = termux_info()
    checks = []
    def add(name, ok, detail, severity="required"):
        checks.append({"name": name, "ok": bool(ok), "detail": str(detail), "severity": severity})
    add("Termux environment", info["is_termux"], info["platform"])
    add("Supported architecture", info["architecture"] in ("aarch64", "arm64"), info["architecture"])
    add("Python 3", sys.version_info >= (3, 9), sys.version.split()[0])
    add("Git", shutil.which("git") is not None, shutil.which("git") or "Not found")
    add("curl", shutil.which("curl") is not None, shutil.which("curl") or "Not found")
    add("OpenSSL", shutil.which("openssl") is not None, shutil.which("openssl") or "Not found", "optional")
    add("Node Core OS installation", info["node_core_installed"], str(HOME / ".node-core" / "app"), "informational")
    try:
        usage = shutil.disk_usage(HOME)
        free_mb = usage.free // (1024 * 1024)
        add("Available storage", free_mb >= 200, f"{free_mb} MB free (200 MB preliminary threshold)")
    except OSError as exc:
        add("Available storage", False, exc)
    return {"environment": info, "checks": checks,
            "summary": {"passed": sum(1 for x in checks if x["ok"]),
                        "failed": sum(1 for x in checks if not x["ok"] and x["severity"] == "required"),
                        "total": len(checks)}}

def load_config():
    STATE.mkdir(parents=True, exist_ok=True)
    if CONFIG.exists():
        data = json.loads(CONFIG.read_text())
        if data.get("bind") != "127.0.0.1" or not isinstance(data.get("port"), int):
            raise RuntimeError("Unsafe or invalid Lobby configuration")
        return data
    data = {"bind":"127.0.0.1","port":8765,"token":secrets.token_urlsafe(32),"https":True}
    CONFIG.write_text(json.dumps(data, indent=2) + "\n")
    CONFIG.chmod(0o600)
    return data

def ensure_certificate():
    if CERT.exists() and KEY.exists():
        return True
    openssl = shutil.which("openssl")
    if not openssl:
        return False
    result = subprocess.run([openssl,"req","-x509","-newkey","rsa:2048","-nodes",
        "-keyout",str(KEY),"-out",str(CERT),"-days","365",
        "-subj","/CN=localhost","-addext","subjectAltName=DNS:localhost,IP:127.0.0.1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if result.returncode == 0:
        KEY.chmod(0o600); CERT.chmod(0o600)
        return True
    return False

class Handler(BaseHTTPRequestHandler):
    server_version = "NodeCoreLobby/0.2"
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self.send_json({"status":"ok","transport":"https" if self.server.is_https else "http"})
        elif path == "/api/diagnostics":
            self.send_json(diagnostics())
        elif path == "/api/status":
            info = termux_info()
            self.send_json({"status":"running","transport":"https" if self.server.is_https else "http","environment":info})
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
        self.send_response(200); self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(data))); self.send_header("Cache-Control","no-store")
        self.end_headers(); self.wfile.write(data)
    def send_json(self, obj):
        data=json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(data))); self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers(); self.wfile.write(data)
    def log_message(self, fmt, *args):
        print("[lobby] " + fmt % args, flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    cfg=load_config()
    if args.check:
        print(json.dumps({"config":str(CONFIG),"bind":cfg["bind"],"port":cfg["port"],"https":cfg["https"],"environment":termux_info()},indent=2)); return 0
    httpd=ThreadingHTTPServer((cfg["bind"],cfg["port"]),Handler)
    httpd.daemon_threads=True; httpd.cfg=cfg
    use_https=bool(cfg.get("https")) and ensure_certificate()
    if use_https:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(str(CERT),str(KEY))
        httpd.socket=context.wrap_socket(httpd.socket,server_side=True)
    httpd.is_https=use_https
    scheme="https" if use_https else "http"
    print(f"NODE CORE OS LOBBY listening on {scheme}://127.0.0.1:{cfg['port']}/",flush=True)
    print("Read-only API. Loopback only; no LAN exposure.",flush=True)
    try: httpd.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt: pass
    finally: httpd.server_close()
    return 0

if __name__=="__main__":
    raise SystemExit(main())
