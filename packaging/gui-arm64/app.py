#!/usr/bin/env python3
"""Local-only responsive browser dashboard for Node Core OS."""
from __future__ import annotations
import html, os, shutil, subprocess, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
VERSION="1.5.6"
DATA=Path.home()/".node-core"
CORE=DATA/"bin"/"node-core"
HOST="127.0.0.1"

def page():
    termux=bool(os.environ.get("TERMUX_VERSION") and os.environ.get("PREFIX"))
    rows={"GUI":VERSION,"Platform":"Termux / Android userland" if termux else "GNU/Linux",
          "Architecture":os.uname().machine,"Core engine":"Installed" if CORE.is_file() else "Not detected",
          "Kubo executable":shutil.which("ipfs") or "Not found","Data directory":str(DATA)}
    table="".join(f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>" for k,v in rows.items())
    action='<form method="post" action="/launch"><button>Launch Node Core terminal</button></form>' if CORE.is_file() else '<p class="warn">Install the original Node Core engine first. GUI does not replace its installer.</p>'
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#101820"><title>Node Core OS</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#101820;color:#e4edf2;font:16px system-ui}}header{{background:#172733;padding:25px}}main{{max-width:850px;margin:auto;padding:22px}}h1{{font-size:clamp(25px,6vw,38px);letter-spacing:.08em;margin:0}}.muted{{color:#8fd8ce}}section{{background:#172733;border:1px solid #29434f;border-radius:14px;padding:20px;margin:18px 0;overflow-wrap:anywhere}}table{{width:100%;border-collapse:collapse}}th,td{{padding:12px 8px;text-align:left;border-bottom:1px solid #29434f}}th{{color:#9bb5c1;width:38%}}button{{background:#16776e;color:white;border:0;border-radius:8px;padding:13px 18px;font-size:1rem}}.warn{{color:#ffd18b}}footer{{color:#91a6b1;font-size:.85rem}}</style><header><main><h1>NODE CORE OS</h1><div class="muted">byLAEV · Local GUI {VERSION}</div></main></header><main><section><h2>Node dashboard</h2><table>{table}</table></section><section><h2>Core operations</h2>{action}<p>Bound to localhost only. No remote access, automatic publishing or privileged operations.</p></section><footer>Local-first infrastructure · Local storage and Kubo/IPFS are separate components.</footer></main></html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/","/status"): self.send_error(404); return
        body=page().encode()
        self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        if self.path!="/launch": self.send_error(404); return
        if not CORE.is_file(): self.send_error(409,"Core engine missing"); return
        term=shutil.which("x-terminal-emulator") or shutil.which("konsole") or shutil.which("gnome-terminal")
        if not term: self.send_error(503,"No supported terminal launcher"); return
        cmd=[term,"--",str(CORE)] if term.endswith("gnome-terminal") else [term,"-e",str(CORE)]
        try:
            subprocess.Popen(cmd,start_new_session=True); self.send_response(303); self.send_header("Location","/"); self.end_headers()
        except OSError as exc: self.send_error(500,str(exc))
    def log_message(self,fmt,*args): print("Node Core GUI:",fmt%args)

def main():
    if os.geteuid()==0: raise SystemExit("Run Node Core GUI as the normal user, never root.")
    with ThreadingHTTPServer((HOST,0),Handler) as server:
        url=f"http://{HOST}:{server.server_port}/"
        print(f"Node Core OS GUI {VERSION}: {url}")
        threading.Timer(.7,lambda:webbrowser.open(url)).start()
        try: server.serve_forever()
        except KeyboardInterrupt: pass
if __name__=="__main__": main()
