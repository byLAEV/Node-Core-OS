#!/usr/bin/env python3
"""Native Termux Lobby with read-only diagnostics and verified package staging."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, hmac, json, os, platform, re, secrets, shutil, socket, ssl, subprocess, sys, tempfile, urllib.error, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from certificate_manager import CertificateManager, CertificateManagerError
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

GITHUB_RELEASE_API = "https://api.github.com/repos/byLAEV/Node-Core-OS/releases/latest"
RELEASE_TIMEOUT = 12.0
RELEASE_MAX_BYTES = 1024 * 1024

def parse_latest_stable_release(payload):
    """Validate the canonical latest stable release and its two package digests."""
    if not isinstance(payload, dict):
        raise ValueError("GitHub release response must be an object")
    if payload.get("draft") is not False or payload.get("prerelease") is not False:
        raise ValueError("GitHub latest release is not a published stable release")
    tag = payload.get("tag_name")
    match = re.fullmatch(r"v([0-9]+\.[0-9]+\.[0-9]+)", tag or "")
    if not match:
        raise ValueError("Release tag is not a stable semantic version")
    version = match.group(1)
    assets_payload = payload.get("assets")
    if not isinstance(assets_payload, list):
        raise ValueError("Release assets are missing")
    expected = {
        f"node-core-os-install-{version}.tar.gz": "install",
        f"node-core-os-update-{version}.tar.gz": "update",
    }
    assets = {}
    for item in assets_payload:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if name not in expected:
            continue
        digest = item.get("digest")
        digest_match = re.fullmatch(r"sha256:([0-9a-f]{64})", digest or "")
        url = item.get("browser_download_url")
        size = item.get("size")
        expected_url = f"https://github.com/byLAEV/Node-Core-OS/releases/download/{tag}/{name}"
        if not digest_match or url != expected_url:
            raise ValueError(f"Release asset metadata is invalid: {name}")
        if not isinstance(size, int) or size <= 0:
            raise ValueError(f"Release asset size is invalid: {name}")
        assets[expected[name]] = {
            "name": name, "url": url, "sha256": digest_match.group(1),
            "size_bytes": size
        }
    if set(assets) != {"install", "update"}:
        raise ValueError("Release must contain exactly the official install and update packages")
    body = payload.get("body") or ""
    for kind in ("install", "update"):
        asset = assets[kind]
        section = body[body.find(asset["name"]):] if asset["name"] in body else ""
        checksum_line = re.search(r"(?m)^SHA-256:\s*([0-9a-f]{64})\s*$", section)
        if not checksum_line or checksum_line.group(1) != asset["sha256"]:
            raise ValueError(f"Published SHA-256 notes do not match the asset digest: {asset['name']}")
    published = payload.get("published_at")
    if not isinstance(published, str) or not published:
        raise ValueError("Release publication timestamp is missing")
    release_url = payload.get("html_url")
    expected_release_url = f"https://github.com/byLAEV/Node-Core-OS/releases/tag/{tag}"
    if release_url != expected_release_url:
        raise ValueError("Release page URL is not the canonical official GitHub URL")
    return {
        "status": "verified_metadata",
        "version": version,
        "tag": tag,
        "name": payload.get("name") or f"Node Core OS {version}",
        "published_at": published,
        "release_url": release_url,
        "assets": assets,
        "verification": {
            "stable_release": True,
            "expected_assets_present": True,
            "asset_digest_format": "GitHub SHA-256 digest",
            "release_notes_checksums_match_asset_digests": True,
            "archive_bytes_downloaded_and_rehashed": False
        }
    }

def latest_stable_release():
    request = urllib.request.Request(
        GITHUB_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Node-Core-OS-Lobby",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    )
    with urllib.request.urlopen(request, timeout=RELEASE_TIMEOUT) as response:
        raw = response.read(RELEASE_MAX_BYTES + 1)
    if len(raw) > RELEASE_MAX_BYTES:
        raise ValueError("GitHub release metadata exceeds the allowed response size")
    payload = json.loads(raw.decode("utf-8"))
    result = parse_latest_stable_release(payload)
    return result

PACKAGE_MAX_BYTES = 300 * 1024 * 1024
PACKAGE_CHUNK_BYTES = 1024 * 1024

def package_receipts():
    package_dir = HOME / ".node-core" / "lobby" / "packages"
    output = []
    if package_dir.is_symlink() or not package_dir.is_dir():
        return {"packages": output}
    for receipt_path in sorted(package_dir.glob("node-core-os-*.tar.gz.json")):
        if receipt_path.is_symlink() or not receipt_path.is_file():
            continue
        try:
            data = json.loads(receipt_path.read_text(encoding="utf-8"))
            if data.get("status") != "sha256_verified":
                continue
            output.append({
                "kind": data.get("kind"),
                "version": data.get("version"),
                "asset_name": data.get("asset_name"),
                "size_bytes": data.get("size_bytes"),
                "actual_sha256": data.get("actual_sha256"),
                "verified_at": data.get("verified_at"),
                "extracted": data.get("extracted", False),
                "executed": data.get("executed", False),
            })
        except (OSError, ValueError, TypeError):
            continue
    return {"packages": output}

def ensure_package_directory():
    base = HOME / ".node-core"
    for path in (base, STATE):
        if path.is_symlink():
            raise ValueError(f"Refusing to use a symlink as Lobby state: {path}")
        if path.exists() and not path.is_dir():
            raise ValueError(f"Lobby state path is not a directory: {path}")
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.stat(base).st_uid != os.getuid() or os.stat(STATE).st_uid != os.getuid():
        raise ValueError("Lobby state directory is not owned by the current user")
    package_dir = STATE / "packages"
    if package_dir.is_symlink():
        raise ValueError(f"Refusing to use a symlink as package storage: {package_dir}")
    if package_dir.exists() and not package_dir.is_dir():
        raise ValueError("Package storage path is not a directory")
    package_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.stat(package_dir).st_uid != os.getuid():
        raise ValueError("Package storage is not owned by the current user")
    package_dir.chmod(0o700)
    return package_dir

def atomic_write_json(path, payload):
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=".metadata-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise

def download_and_verify_release_package(kind, release=None):
    """Download one canonical release package and verify its complete SHA-256."""
    if kind not in ("install", "update"):
        raise ValueError("Package kind must be 'install' or 'update'")
    if release is None:
        release = latest_stable_release()
    if release.get("status") != "verified_metadata":
        raise ValueError("Stable release metadata has not been verified")
    asset = release.get("assets", {}).get(kind)
    if not isinstance(asset, dict):
        raise ValueError(f"The verified release has no {kind} package")
    expected_name = f"node-core-os-{kind}-{release['version']}.tar.gz"
    expected_url = (
        f"https://github.com/byLAEV/Node-Core-OS/releases/download/"
        f"{release['tag']}/{expected_name}"
    )
    digest = asset.get("sha256")
    size = asset.get("size_bytes")
    if asset.get("name") != expected_name or asset.get("url") != expected_url:
        raise ValueError("Release package identity or download URL is not canonical")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("Release package SHA-256 metadata is invalid")
    if not isinstance(size, int) or size <= 0 or size > PACKAGE_MAX_BYTES:
        raise ValueError("Release package size is outside the permitted limit")

    package_dir = ensure_package_directory()
    final_path = package_dir / expected_name
    receipt_path = package_dir / f"{expected_name}.json"
    if final_path.is_symlink() or receipt_path.is_symlink():
        raise ValueError("Refusing to replace a symlink in package storage")

    request = urllib.request.Request(
        expected_url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": "Node-Core-OS-Lobby",
        }
    )
    fd, temporary = tempfile.mkstemp(
        prefix=f".{kind}-{release['version']}-", suffix=".part", dir=str(package_dir)
    )
    digestor = hashlib.sha256()
    total = 0
    try:
        with os.fdopen(fd, "wb") as output:
            with urllib.request.urlopen(request, timeout=60.0) as response:
                parsed_url = urllib.parse.urlparse(response.geturl())
                allowed_hosts = {
                    "release-assets.githubusercontent.com",
                    "objects.githubusercontent.com",
                    "github.com",
                }
                if parsed_url.scheme != "https" or parsed_url.hostname not in allowed_hosts:
                    raise ValueError("GitHub redirected the package download to an untrusted host")
                while True:
                    chunk = response.read(PACKAGE_CHUNK_BYTES)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > size or total > PACKAGE_MAX_BYTES:
                        raise ValueError("Downloaded package exceeds the published size")
                    digestor.update(chunk)
                    output.write(chunk)
            output.flush()
            os.fsync(output.fileno())

        actual_digest = digestor.hexdigest()
        if total != size:
            raise ValueError(f"Downloaded size mismatch: expected {size}, received {total}")
        if not hmac.compare_digest(actual_digest, digest):
            raise ValueError("Downloaded package SHA-256 does not match the official Release")

        os.chmod(temporary, 0o600)
        os.replace(temporary, final_path)
        receipt = {
            "status": "sha256_verified",
            "kind": kind,
            "version": release["version"],
            "tag": release["tag"],
            "release_url": release["release_url"],
            "asset_name": expected_name,
            "size_bytes": total,
            "expected_sha256": digest,
            "actual_sha256": actual_digest,
            "verified_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "archive_inspected": False,
            "extracted": False,
            "executed": False,
        }
        atomic_write_json(receipt_path, receipt)
        return receipt
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise

def load_config():
    base_state = HOME / ".node-core"
    if base_state.is_symlink() or STATE.is_symlink():
        raise RuntimeError("Refusing to use a symlink as Node Core OS Lobby state")
    base_state.mkdir(mode=0o700, parents=True, exist_ok=True)
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if CONFIG.is_symlink():
        raise RuntimeError("Refusing to load Lobby configuration through a symlink")
    if CONFIG.exists():
        data = json.loads(CONFIG.read_text())
        if data.get("bind") != "127.0.0.1" or not isinstance(data.get("port"), int) or not 1 <= data["port"] <= 65535:
            raise RuntimeError("Unsafe or invalid Lobby configuration")
        if not isinstance(data.get("token"), str) or len(data["token"]) < 40:
            data["token"] = secrets.token_urlsafe(32)
            atomic_write_json(CONFIG, data)
        return data
    data = {"bind": "127.0.0.1", "port": 8765, "token": secrets.token_urlsafe(32), "https": True}
    atomic_write_json(CONFIG, data)
    return data

def ensure_certificate():
    """Return True only when a usable localhost certificate/key pair exists."""
    openssl = shutil.which("openssl")
    if not openssl:
        return False

    if CERT.is_file() and KEY.is_file():
        valid = subprocess.run(
            [openssl, "x509", "-in", str(CERT), "-noout", "-checkend", "0"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
        )
        if valid.returncode == 0:
            try:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(str(CERT), str(KEY))
                return True
            except (OSError, ssl.SSLError):
                pass

    # Generate into temporary files first. Do not leave a partial certificate
    # pair at the active paths if OpenSSL fails.
    temp_cert = STATE / ("localhost.crt.new." + str(os.getpid()))
    temp_key = STATE / ("localhost.key.new." + str(os.getpid()))
    try:
        result = subprocess.run([
            openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(temp_key), "-out", str(temp_cert), "-days", "365",
            "-subj", "/CN=localhost",
            "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
           check=False, timeout=45)
        if result.returncode != 0 or not temp_cert.is_file() or not temp_key.is_file():
            return False
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(temp_cert), str(temp_key))
        temp_key.chmod(0o600)
        temp_cert.chmod(0o600)
        os.replace(temp_key, KEY)
        os.replace(temp_cert, CERT)
        return True
    except (OSError, ssl.SSLError, subprocess.TimeoutExpired):
        return False
    finally:
        for path in (temp_cert, temp_key):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

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
        elif path == "/api/packages/status":
            self.send_json(package_receipts())
        elif path == "/api/certificates":
            try:
                self.send_json(CertificateManager().inventory())
            except (CertificateManagerError, OSError, ValueError) as exc:
                self.send_json({"status": "unavailable", "message": str(exc)[:300]})
        elif path == "/api/releases/latest":
            try:
                release = latest_stable_release()
                node = detect_node_core()
                installed = node.get("version")
                release["installed_version"] = installed
                release["installation_detected"] = node.get("installed", False)
                release["partial_installation"] = node.get("partial_or_residual", False)
                release["installation_status"] = node.get("status", "unknown")
                release["local_transport"] = "https" if self.server.is_https else "http"
                try:
                    release["update_available"] = bool(
                        installed and tuple(map(int, release["version"].split("."))) >
                        tuple(map(int, installed.split(".")))
                    )
                except (AttributeError, TypeError, ValueError):
                    release["update_available"] = False
                self.send_json(release)
            except (OSError, urllib.error.URLError, urllib.error.HTTPError,
                    ValueError, json.JSONDecodeError, TimeoutError) as exc:
                self.send_json({
                    "status": "unavailable",
                    "error": str(exc)[:240],
                    "message": "The latest stable release could not be verified. No installation or update was started."
                })
        elif path in ("/", "/index.html"):
            self.send_file(WEB / "index.html", "text/html; charset=utf-8")
        elif path == "/manifest.webmanifest":
            self.send_file(WEB / "manifest.webmanifest", "application/manifest+json")
        elif path == "/icon.svg":
            self.send_file(WEB / "icon.svg", "image/svg+xml")
        else:
            self.send_error(404)
    def do_POST(self):
        path = urlparse(self.path).path
        try:
            self.require_local_authorization()
            if path not in ("/api/packages/prepare", "/api/certificates/action"):
                self.send_json({"status": "error", "message": "Unknown operation"})
                return
            length_text = self.headers.get("Content-Length", "")
            if not length_text.isdigit():
                self.send_json({"status": "error", "message": "Invalid request length"})
                return
            length = int(length_text)
            maximum_body = 128 * 1024 if path == "/api/certificates/action" else 4096
            if length < 1 or length > maximum_body:
                self.send_json({"status": "error", "message": "Request body size is invalid"})
                return
            if self.headers.get_content_type() != "application/json":
                self.send_json({"status": "error", "message": "Content-Type must be application/json"})
                return
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                self.send_json({"status": "error", "message": "Request body must be a JSON object"})
                return
            if path == "/api/certificates/action":
                action = payload.get("action")
                result = CertificateManager().execute(action, payload)
                self.send_json({
                    "status": "success",
                    "result": result,
                    "message": "Certificate operation completed and locally validated. Restart the Lobby if requested."
                })
                return
            kind = payload.get("kind")
            receipt = download_and_verify_release_package(kind)
            self.send_json({
                "status": "verified",
                "receipt": receipt,
                "message": "Package downloaded and SHA-256 verified. It has not been extracted or executed."
            })
        except PermissionError as exc:
            self.send_json({"status": "forbidden", "message": str(exc)})
        except (OSError, urllib.error.URLError, urllib.error.HTTPError,
                CertificateManagerError, ValueError, json.JSONDecodeError, TimeoutError) as exc:
            self.send_json({
                "status": "error",
                "message": str(exc)[:300],
                "operation_started": False
            })

    def require_local_authorization(self):
        if not getattr(self.server, "is_https", False):
            raise PermissionError("Package staging requires HTTPS on the local Lobby connection")
        expected_token = self.server.config.get("token", "")
        supplied_token = self.headers.get("X-Node-Core-Lobby-Token", "")
        if not isinstance(expected_token, str) or not expected_token or not hmac.compare_digest(
            supplied_token, expected_token
        ):
            raise PermissionError("Local Lobby authorization failed")

        host = self.headers.get("Host", "")
        hostname = host.rsplit(":", 1)[0].strip("[]").lower() if ":" in host else host.lower()
        port_text = host.rsplit(":", 1)[1] if ":" in host else ""
        if hostname not in ("127.0.0.1", "localhost") or port_text != str(self.server.server_port):
            raise PermissionError("Host header is not the local Lobby host")

        origin = self.headers.get("Origin", "")
        scheme = "https" if getattr(self.server, "is_https", False) else "http"
        if origin not in (
            f"{scheme}://127.0.0.1:{self.server.server_port}",
            f"{scheme}://localhost:{self.server.server_port}",
        ):
            raise PermissionError("Request origin is not the local Lobby origin")

    def send_file(self, path, content_type):
        data = path.read_bytes()
        if path.name == "index.html":
            marker = b"<!-- NODE_CORE_LOBBY_SESSION -->"
            session_script = (
                b"<script>window.NODE_CORE_LOBBY_SESSION = "
                + json.dumps(self.server.config["token"]).encode("ascii")
                + b";</script>"
            )
            data = data.replace(marker, session_script)
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
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
    httpd.config = cfg
    use_https = bool(cfg.get("https")) and ensure_certificate()
    if use_https:
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(CERT), str(KEY))
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        except (OSError, ssl.SSLError) as exc:
            print(f"TLS setup failed; using HTTP loopback fallback: {exc}", file=sys.stderr, flush=True)
            use_https = False
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
