#!/data/data/com.termux/files/usr/bin/python
"""Read-only local diagnostic lobby for Termux. Standard library only."""
import json, os, platform, shutil, socket, subprocess, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOME = Path.home()
PREFIX = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
PORT = 8765

def run(args):
    try:
        p = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=8)
        return {"exit_code": p.returncode, "output": p.stdout.strip()[:12000]}
    except Exception as exc:
        return {"error": str(exc)}

def diagnostic():
    packages = run(["pkg", "list-installed"]) if shutil.which("pkg") else {"error": "pkg no disponible"}
    return {
        "timestamp_unix": int(time.time()),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "termux": {
            "prefix": str(PREFIX), "home": str(HOME),
            "termux_version": os.environ.get("TERMUX_VERSION", "no expuesta"),
            "packages": packages
        },
        "node_core_os": {
            "home_directory": str(HOME / ".node-core"),
            "installed": (HOME / ".node-core" / "VERSION").exists() or (HOME / "Node-Core-OS").exists(),
            "candidate_paths": [str(HOME / ".node-core"), str(HOME / "Node-Core-OS")]
        },
        "network": {
            "hostname": socket.gethostname(),
            "localhost_resolution": run(["getent", "hosts", "localhost"]) if shutil.which("getent") else {"output": "getent no disponible"},
            "interfaces": run(["ip", "-brief", "address"]) if shutil.which("ip") else {"output": "ip no disponible"}
        },
        "storage": {
            "home": run(["df", "-h", str(HOME)]),
            "home_entries": sorted(p.name + ("/" if p.is_dir() else "") for p in HOME.iterdir())[:500]
        },
        "tools": {name: shutil.which(name) for name in ["python", "git", "curl", "openssl", "ip", "pkg", "termux-open-url", "kubo", "ipfs"]}
    }

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"status":"online","transport":"HTTP","host":"127.0.0.1","port":PORT}).encode()
            self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8")
        elif self.path == "/api/diagnostics":
            body = json.dumps(diagnostic(), ensure_ascii=False, indent=2).encode()
            self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8")
        elif self.path in ("/", "/index.html"):
            body = (Path(__file__).with_name("index.html").read_text(encoding="utf-8")).encode()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
        else:
            body = b'{"error":"not found"}'
            self.send_response(404); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(body)
    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("NODE CORE OS Lobby listening on http://127.0.0.1:%d/" % PORT, flush=True)
    server.serve_forever()
