#!/usr/bin/env python3
"""Read-only Linux distribution, terminal and architecture detection for Node Core OS Lobby."""
from __future__ import annotations
import argparse, hashlib, json, os, platform, shlex, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

SUPPORTED_ARCHITECTURES={"x86_64","aarch64"}
REQUIRED=("bash","python3","tar","sha512sum","mkdir","cp","rm","mktemp","uname","awk","realpath","stat","id","find","grep","sed","nohup")
MANAGERS=(("apt-get","APT"),("dnf","DNF"),("yum","YUM"),("pacman","Pacman"),("zypper","Zypper"),("apk","Alpine APK"),("xbps-install","XBPS"),("emerge","Portage"))

def _os_release(path):
    values={}
    try: lines=path.read_text(encoding="utf-8",errors="replace").splitlines()
    except OSError: return values
    for line in lines:
        if not line or line.startswith("#") or "=" not in line: continue
        key,raw=line.split("=",1)
        if key not in {"ID","ID_LIKE","NAME","PRETTY_NAME","VERSION_ID"}: continue
        try:
            parsed=shlex.split(raw,comments=False,posix=True)
            if len(parsed)==1: values[key]=parsed[0]
        except ValueError: pass
    return values

def detect_host_environment(environ=None, *, system=None, machine=None, kernel_release=None,
                            os_release_path=Path("/etc/os-release"), command_lookup=None,
                            python_version=None):
    env=dict(os.environ if environ is None else environ)
    system=system or platform.system()
    machine=machine or platform.machine()
    kernel=kernel_release or platform.release()
    lookup=command_lookup or shutil.which
    py=python_version or tuple(sys.version_info[:3])
    arch={"amd64":"x86_64","arm64":"aarch64","armv8":"aarch64","armv8l":"aarch64"}.get(machine.lower(),machine.lower())
    termux=bool(env.get("TERMUX_VERSION") and env.get("PREFIX","").startswith("/data/data/com.termux/"))
    linux=system=="Linux"
    osr=_os_release(Path(os_release_path))
    wsl=bool(env.get("WSL_DISTRO_NAME") or env.get("WSL_INTEROP") or "microsoft" in kernel.lower() or "wsl" in kernel.lower())
    container=env.get("container")
    if not container:
        for marker,label in ((Path("/.dockerenv"),"docker"),(Path("/run/.containerenv"),"podman")):
            if marker.exists(): container=label; break
    if termux:
        profile="termux"; kind="native_termux"; distro={"id":"termux","name":"Termux","version_id":env.get("TERMUX_VERSION"),"pretty_name":"Termux on Android"}
    elif linux:
        profile="gnu_linux"; kind="wsl" if wsl else ("linux_container" if container else "gnu_linux")
        distro={"id":osr.get("ID","unknown").lower(),"name":osr.get("NAME","Unknown GNU/Linux"),"version_id":osr.get("VERSION_ID"),"pretty_name":osr.get("PRETTY_NAME",osr.get("NAME","GNU/Linux")),"id_like":osr.get("ID_LIKE","").lower().split()}
    else:
        profile="unsupported"; kind="unsupported"; distro={"id":system.lower(),"name":system,"version_id":None,"pretty_name":system}
    terminal=next(((label or env.get(key),key) for key,label in (("TERM_PROGRAM",None),("LC_TERMINAL",None),("KONSOLE_VERSION","Konsole"),("GNOME_TERMINAL_SCREEN","GNOME Terminal"),("WT_SESSION","Windows Terminal"),("VSCODE_INJECTION","VS Code")) if env.get(key)),(None,None))
    if not terminal[0] and env.get("TERM"): terminal=("Terminal compatible with "+env["TERM"],"TERM")
    manager=None
    if termux and lookup("pkg"): manager={"id":"pkg","name":"Termux pkg","path":lookup("pkg")}
    elif linux:
        for cmd,label in MANAGERS:
            if lookup(cmd): manager={"id":cmd,"name":label,"path":lookup(cmd)}; break
    missing=[cmd for cmd in REQUIRED if not lookup(cmd)]
    downloaders=[cmd for cmd in ("curl","wget") if lookup(cmd)]
    if not downloaders: missing.append("curl or wget")
    if py<(3,10,0): missing.append("Python 3.10 or newer")
    if termux and not manager: missing.append("pkg")
    arch_ok=arch in SUPPORTED_ARCHITECTURES
    supported=linux and arch_ok and profile in ("termux","gnu_linux")
    readiness="unsupported" if not supported else ("requires_preparation" if missing else "ready")
    fingerprint_data={"profile":profile,"kind":kind,"distribution":distro["id"],"version":distro.get("version_id"),"architecture":arch}
    fingerprint=hashlib.sha256(json.dumps(fingerprint_data,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {"platform":distro["pretty_name"],"operating_system":system,"is_linux":linux,"is_termux":termux,
      "profile":profile,"environment_type":kind,"profile_supported":supported,"preflight_status":readiness,
      "supported_architecture":arch_ok,"architecture":arch,"machine":machine,"kernel":kernel,"distribution":distro,
      "package_manager":manager,"terminal":{"emulator":terminal[0] or "Unknown terminal emulator","detection_source":terminal[1],"term":env.get("TERM"),"shell":Path(env.get("SHELL","")).name or None},
      "python":".".join(map(str,py)),"python_supported":py>=(3,10,0),"python_executable":sys.executable,
      "termux_version":env.get("TERMUX_VERSION"),"prefix":env.get("PREFIX"),"home":env.get("HOME") or str(Path.home()),
      "container":container,"wsl":wsl,"available_commands":{c:lookup(c) for c in REQUIRED if lookup(c)},
      "available_downloaders":downloaders,"missing_capabilities":missing,"fingerprint_sha256":fingerprint,
      "installer":{"entry_point":"bash installer/install.sh","selection":"One official installer evaluates NCTCL capabilities; no distro-specific Lobby installer."}}

def create_installation_snapshot(environ=None):
    return {"schema_version":1,"installed_at_utc":datetime.now(timezone.utc).isoformat(),"host":detect_host_environment(environ)}

def read_installation_snapshot(path):
    try:
        if Path(path).is_symlink() or not Path(path).is_file(): return None
        data=json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data,dict) and data.get("schema_version")==1 and isinstance(data.get("host"),dict) else None
    except (OSError,ValueError,TypeError): return None

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--snapshot",action="store_true")
    args=parser.parse_args()
    print(json.dumps(create_installation_snapshot() if args.snapshot else detect_host_environment(),indent=2,sort_keys=True))
