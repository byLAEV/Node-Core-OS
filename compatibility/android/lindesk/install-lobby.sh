#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
fail(){ echo "LOBBY INSTALL ERROR: $*" >&2; exit 1; }
[[ "$(id -u)" != 0 ]] || fail "Do not run as root."
. /etc/os-release
[[ "${ID:-}" == debian && "$(uname -m)" == aarch64 ]] || fail "Requires Debian ARM64."
for c in bash curl python3; do command -v "$c" >/dev/null || fail "Missing $c"; done
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SRC="$ROOT/compatibility/termux/lobby"
MANIFEST="$ROOT/installer/layout-manifest.json"
DEST="$HOME/.node-core/lobby"
VENV="$HOME/.node-core/runtime/lobby-venv"
BIN="$HOME/.local/bin"
for f in server.py certificate_manager.py bitcoin_identity.py certificates/catalog.json web/index.html web/manifest.webmanifest web/icon.svg; do [[ -f "$SRC/$f" && ! -L "$SRC/$f" ]] || fail "Missing Lobby source: $f"; done
[[ -f "$MANIFEST" ]] || fail "Missing layout manifest."
for p in "$HOME/.node-core" "$DEST" "$VENV" "$BIN" "$BIN/node-core-lobby"; do [[ ! -L "$p" ]] || fail "Refusing symlink: $p"; done
mkdir -p "$HOME/.node-core/runtime" "$BIN"
[[ -x "$VENV/bin/python" ]] || python3 -m venv "$VENV" || fail "Cannot create venv."
PY="$VENV/bin/python"
"$PY" -m pip --version >/dev/null 2>&1 || "$PY" -m ensurepip --upgrade
"$PY" -m pip install --only-binary=:all: cryptography || fail "cryptography wheel unavailable."
"$PY" -c 'import cryptography; print(cryptography.__version__)' || fail "cryptography import failed."
"$PY" - "$SRC" "$MANIFEST" <<'PY'
import ast,json,sys
from pathlib import Path
p=Path(sys.argv[1])
for n in ("server.py","certificate_manager.py","bitcoin_identity.py"): ast.parse((p/n).read_text())
json.loads((p/"certificates/catalog.json").read_text())
json.loads(Path(sys.argv[2]).read_text())
print("Source validation: OK")
PY
T="$(mktemp -d "$HOME/.node-core-lobby-stage.XXXXXX")"; trap 'rm -rf "$T"' EXIT
mkdir -p "$T/web" "$T/certificates" "$T/manifests"
cp "$SRC/server.py" "$SRC/certificate_manager.py" "$SRC/bitcoin_identity.py" "$T/"
cp "$SRC/certificates/catalog.json" "$T/certificates/"
cp "$MANIFEST" "$T/manifests/layout-manifest.json"
cp "$SRC/web/index.html" "$SRC/web/manifest.webmanifest" "$SRC/web/icon.svg" "$T/web/"
cat > "$T/launcher.sh" <<'LAUNCHER'
#!/usr/bin/env bash
set -Eeuo pipefail
B="$HOME/.node-core/lobby"; P="$HOME/.node-core/runtime/lobby-venv/bin/python"; S="$B/server.py"; L="$B/lobby.log"; F="$B/server.pid"
[[ -x "$P" && -f "$S" ]] || { echo "Lobby runtime missing" >&2; exit 1; }
mkdir -p "$B"; touch "$L"; chmod 600 "$L"
if [[ -f "$F" ]]; then old="$(cat "$F" 2>/dev/null || true)"; if [[ "$old" =~ ^[0-9]+$ ]] && [[ -r "/proc/$old/cmdline" ]] && tr '\0' '\n' < "/proc/$old/cmdline" | grep -Fx "$S" >/dev/null; then kill "$old" 2>/dev/null || true; fi; rm -f "$F"; fi
nohup "$P" "$S" >>"$L" 2>&1 </dev/null & pid=$!; echo "$pid" > "$F"; chmod 600 "$F"
url=""
for _ in {1..40}; do
 if curl -kfsS https://127.0.0.1:8765/health >/dev/null 2>&1; then url=https://127.0.0.1:8765/; break; fi
 if curl -fsS http://127.0.0.1:8765/health >/dev/null 2>&1; then url=http://127.0.0.1:8765/; break; fi
 kill -0 "$pid" 2>/dev/null || break; sleep .25
done
[[ -n "$url" ]] || { tail -n 60 "$L" >&2; exit 1; }
echo "NODE CORE OS Lobby: $url"
command -v xdg-open >/dev/null 2>&1 && xdg-open "$url" >/dev/null 2>&1 || true
LAUNCHER
chmod 700 "$T/launcher.sh"
mkdir -p "$DEST/web" "$DEST/certificates" "$DEST/manifests"
for f in server.py certificate_manager.py bitcoin_identity.py certificates/catalog.json manifests/layout-manifest.json web/index.html web/manifest.webmanifest web/icon.svg; do
 [[ ! -L "$DEST/$f" ]] || fail "Refusing symlink target: $f"
 install -m 600 "$T/$f" "$DEST/$f"
done
install -m 700 "$T/launcher.sh" "$DEST/launcher.sh"
install -m 700 "$T/launcher.sh" "$BIN/node-core-lobby"
chmod 700 "$DEST" "$DEST/web" "$DEST/certificates" "$DEST/manifests"
"$PY" "$DEST/server.py" --check >/dev/null || fail "Lobby server check failed."
bash "$BIN/node-core-lobby"
echo "Lobby installed only. Node Core OS was not installed."
