#!/usr/bin/env python3
"""Local-only Node Core OS Lobby server for Termux (Python standard library)."""
from __future__ import annotations
import argparse, json, os, secrets, ssl, subprocess, sys, threading, time
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
    return {
        "platform": "Android / Termux" if os.environ.get("TERMUX_VERSION") or os.environ.get("PREFIX", "").startswith("/data/data/com.termux") else sys.platform,
        "architecture": os.uname().machine,
        "python": sys.version.split()[0],
        "prefix": os.environ.get("PREFIX", "not detected"),
        "home": str(HOME),
        "node_core_installed": (HOME / ".node-core" / "app").is_dir(),
    }

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
    # Use Termux OpenSSL to create a self-signed localhost certificate.
    openssl = shutil_which("openssl")
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

def shutil_which(name):
    from shutil import which
    return which(name)

class Handler(BaseHTTPRequestHandler):
    server_version = "NodeCoreLobby/0.1"
    def do_GET(self):
        cfg = self.server.cfg
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.send_json({"status":"ok","transport":"https" if self.server.is_https else "http"})
            return
        if parsed.path == "/api/status":
            if not secrets.compare_digest(self.headers.get("X-Node-Core-Token",""), cfg["token"]):
                self.send_error(403); return
            self.send_json({"status":"running","transport":"https" if self.server.is_https else "http","environment":termux_info()})
            return
        if parsed.path == "/" or parsed.path == "/index.html":
            page = (WEB / "index.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(page))); self.send_header("Cache-Control","no-store")
            self.end_headers(); self.wfile.write(page); return
        if parsed.path == "/manifest.webmanifest":
            data = (WEB / "manifest.webmanifest").read_bytes()
            self.send_response(200); self.send_header("Content-Type","application/manifest+json")
            self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data); return
        if parsed.path == "/icon.svg":
            data = (WEB / "icon.svg").read_bytes()
            self.send_response(200); self.send_header("Content-Type","image/svg+xml")
            self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data); return
        self.send_error(404)
    def send_json(self, obj):
        data=json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(data))); self.send_header("Cache-Control","no-store")
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
    httpd.daemon_threads=True
    httpd.cfg=cfg
    use_https=bool(cfg.get("https")) and ensure_certificate()
    if use_https:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(str(CERT),str(KEY))
        httpd.socket=context.wrap_socket(httpd.socket,server_side=True)
    httpd.is_https=use_https
    scheme="https" if use_https else "http"
    print(f"NODE CORE OS LOBBY listening on {scheme}://127.0.0.1:{cfg['port']}/",flush=True)
    print("Loopback-only server. Do not expose this port to a network interface.",flush=True)
    try: httpd.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt: pass
    finally: httpd.server_close()
    return 0

if __name__=="__main__":
    raise SystemExit(main())
