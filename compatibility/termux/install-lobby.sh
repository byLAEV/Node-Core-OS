#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

usage() {
  cat <<'EOF'
NODE CORE OS Lobby installer

Usage:
  bash compatibility/termux/install-lobby.sh [--yes]

Options:
  --yes   Approve installation of the missing OpenSSL package on Termux.
EOF
}

ASSUME_YES=0
for arg in "$@"; do
  case "$arg" in
    --yes) ASSUME_YES=1 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$arg" >&2; usage >&2; exit 2 ;;
  esac
done

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
info() { printf '[LOBBY INSTALL] %s\n' "$*"; }
warn() { printf '[LOBBY INSTALL] WARNING: %s\n' "$*" >&2; }

if [[ "$(uname -s)" != "Linux" ]]; then
  fail "The Lobby currently supports Linux terminal environments only."
fi
if [[ "$(id -u)" == "0" ]]; then
  fail "Do not run this installer as root."
fi
[[ -n "${HOME:-}" && -d "$HOME" ]] || fail "HOME is missing or unavailable."

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
HOST_MODULE="$SOURCE/lobby/host_environment.py"
SOURCE="$ROOT/compatibility/termux"
DEST="$HOME/.node-core/lobby"
if [[ -n "${TERMUX_VERSION:-}" && "${PREFIX:-}" == /data/data/com.termux/files/usr ]]; then
  SHORTCUTS="$HOME/.shortcuts"
else
  SHORTCUTS="$HOME/.local/bin"
fi
SHORTCUT="$SHORTCUTS/node-core-lobby"
PORT=8765

for file in \
  "$SOURCE/lobby/server.py" \
  "$SOURCE/lobby/certificate_manager.py" \
  "$SOURCE/lobby/bitcoin_identity.py" \
  "$SOURCE/lobby/host_environment.py" \
  "$SOURCE/lobby/certificates/catalog.json" \
  "$ROOT/installer/layout-manifest.json" \
  "$SOURCE/lobby/launcher.sh" \
  "$SOURCE/lobby/web/index.html" \
  "$SOURCE/lobby/web/manifest.webmanifest" \
  "$SOURCE/lobby/web/icon.svg"; do
  [[ -f "$file" && ! -L "$file" ]] || fail "Required source file is missing or is a symlink: $file"
done

command -v python >/dev/null 2>&1 || fail "Python is required. Run: pkg install python"
command -v curl >/dev/null 2>&1 || fail "curl is required. Run: pkg install curl"
command -v bash >/dev/null 2>&1 || fail "Bash is required."
if [[ -n "${TERMUX_VERSION:-}" && "${PREFIX:-}" == /data/data/com.termux/files/usr ]]; then
  command -v pkg >/dev/null 2>&1 || fail "Termux package manager pkg was not found."
fi
command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 || fail "Python 3 is required."

if ! python3 -c 'import cryptography' >/dev/null 2>&1 && ! python -c 'import cryptography' >/dev/null 2>&1; then
  if [[ -n "${TERMUX_VERSION:-}" && "${PREFIX:-}" == /data/data/com.termux/files/usr ]]; then
    info "Installing the required Termux Python cryptography package."
    pkg install -y python-cryptography || fail "Could not install python-cryptography."
  else
    fail "Python cryptography is required. Install it using your distribution policy before installing the Lobby."
  fi
fi

# Never follow an unexpected symlink into an existing user data directory.
for path in "$HOME/.node-core" "$DEST" "$DEST/web" "$DEST/certificates" "$DEST/manifests" "$SHORTCUTS" "$SHORTCUT"; do
  [[ ! -L "$path" ]] || fail "Refusing to install through symlink: $path"
done
for target in "$DEST/server.py" "$DEST/certificate_manager.py" "$DEST/bitcoin_identity.py" "$DEST/certificates/catalog.json" "$DEST/manifests/layout-manifest.json" "$DEST/web/index.html" "$DEST/web/manifest.webmanifest" "$DEST/web/icon.svg" "$SHORTCUT"; do
  [[ ! -e "$target" || -f "$target" ]] || fail "Refusing to replace a non-file path: $target"
done

if ! command -v openssl >/dev/null 2>&1; then
  warn "OpenSSL CLI is missing. HTTPS cannot start until openssl-tool is installed."
  install_openssl=0
  if (( ASSUME_YES )); then
    install_openssl=1
  elif [[ -t 0 ]]; then
    printf 'Install Termux package openssl-tool now? [y/N] '
    read -r answer
    case "$answer" in y|Y|yes|YES) install_openssl=1 ;; esac
  fi
  if (( install_openssl )) && [[ -n "${TERMUX_VERSION:-}" && "${PREFIX:-}" == /data/data/com.termux/files/usr ]]; then
    pkg install openssl-tool -y || warn "Package installation failed; the server will use HTTP loopback fallback."
  else
    warn "OpenSSL is unavailable. Install it with the native package manager for this environment; HTTP loopback fallback will be used."
  fi
fi

command -v openssl >/dev/null 2>&1 || warn "OpenSSL is still unavailable; HTTPS will not be available until it is installed."

mkdir -p "$HOME/.node-core" "$DEST/web" "$DEST/certificates" "$DEST/manifests" "$SHORTCUTS"
STAGE="$(mktemp -d "$HOME/.node-core-lobby-stage.XXXXXX")"
BACKUP="$STAGE/backup"
mkdir -p "$BACKUP"
COMMITTED=0
TARGETS=(
  "$DEST/server.py"
  "$DEST/certificate_manager.py"
  "$DEST/bitcoin_identity.py"
  "$DEST/host_environment.py"
  "$DEST/certificates/catalog.json"
  "$DEST/manifests/layout-manifest.json"
  "$DEST/web/index.html"
  "$DEST/web/manifest.webmanifest"
  "$DEST/web/icon.svg"
  "$SHORTCUT"
)
SOURCES=(
  "$SOURCE/lobby/server.py"
  "$SOURCE/lobby/certificate_manager.py"
  "$SOURCE/lobby/bitcoin_identity.py"
  "$SOURCE/lobby/host_environment.py"
  "$SOURCE/lobby/certificates/catalog.json"
  "$ROOT/installer/layout-manifest.json"
  "$SOURCE/lobby/web/index.html"
  "$SOURCE/lobby/web/manifest.webmanifest"
  "$SOURCE/lobby/web/icon.svg"
  "$SOURCE/lobby/launcher.sh"
)

cleanup() {
  rc=$?
  if (( rc != 0 && COMMITTED == 0 )); then
    warn "Installation did not complete. Restoring previously installed Lobby files."
    for i in "${!TARGETS[@]}"; do
      target="${TARGETS[$i]}"
      backup="$BACKUP/$i"
      if [[ -f "$backup" ]]; then
        mkdir -p "$(dirname "$target")"
        cp -p "$backup" "$target" || warn "Could not restore $target"
      else
        rm -f "$target" 2>/dev/null || true
      fi
    done
    if [[ -f "$SHORTCUT" ]]; then
      bash "$SHORTCUT" >/dev/null 2>&1 || warn "Previous Lobby files were restored, but the previous service did not restart automatically."
    fi
  fi
  rm -rf "$STAGE"
}
trap cleanup EXIT

info "Checking Python syntax before installation."
python3 -c 'import ast,json,pathlib,sys; root=pathlib.Path(sys.argv[1]); [ast.parse((root/name).read_text(encoding="utf-8")) for name in ("server.py","certificate_manager.py","bitcoin_identity.py","host_environment.py")]; json.loads((root/"certificates/catalog.json").read_text(encoding="utf-8"))' "$SOURCE/lobby" || fail "Lobby server, certificate manager, Bitcoin identity module or certificate catalog validation failed."

info "Staging Lobby files."
for i in "${!TARGETS[@]}"; do
  target="${TARGETS[$i]}"
  source="${SOURCES[$i]}"
  if [[ -f "$target" ]]; then
    cp -p "$target" "$BACKUP/$i"
  fi
  cp "$source" "$STAGE/$i"
done

info "Installing the Lobby application files."
for i in "${!TARGETS[@]}"; do
  target="${TARGETS[$i]}"
  temp="$target.new.$$"
  cp "$STAGE/$i" "$temp"
  if [[ "$target" == "$SHORTCUT" ]]; then
    chmod 700 "$temp"
  else
    chmod 600 "$temp"
  fi
  mv -f "$temp" "$target"
done
chmod 700 "$DEST" "$DEST/web" "$DEST/certificates" "$DEST/manifests"
chmod 600 "$DEST/server.py" "$DEST/certificate_manager.py" "$DEST/bitcoin_identity.py" "$DEST/certificates/catalog.json" "$DEST/web/index.html" "$DEST/web/manifest.webmanifest" "$DEST/web/icon.svg"

info "Validating the installed server configuration."
python3 "$DEST/server.py" --check >/dev/null || fail "Installed server configuration validation failed."

info "Recording the Linux terminal environment used for this Lobby installation."
python3 "$DEST/host_environment.py" --snapshot > "$STAGE/host-environment.json" || fail "Could not detect the Linux installation environment."
python3 - "$STAGE/host-environment.json" "$DEST/host-environment.json" <<'PY'
import json, os, pathlib, sys, tempfile
source, target = map(pathlib.Path, sys.argv[1:])
payload = json.loads(source.read_text(encoding="utf-8"))
if payload["host"]["preflight_status"] != "ready":
    raise SystemExit("The current Linux environment does not meet Lobby compatibility prerequisites: " + ", ".join(payload["host"]["missing_capabilities"]))
target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
fd, temporary = tempfile.mkstemp(prefix=".host-environment.", dir=target.parent)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump(payload, output, indent=2, sort_keys=True)
        output.write("\\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)
finally:
    if os.path.exists(temporary): os.unlink(temporary)
PY
info "Lobby files staged and configuration validated."
info "Existing server.json, certificates, logs and PID state were preserved."
info "Starting/restarting the local Lobby service."
bash "$SHORTCUT"

printf '\n'
if curl -kfsS "https://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  info "HTTPS health check: PASS"
  printf 'Open: https://127.0.0.1:%s/\n' "$PORT"
elif curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  warn "HTTPS is not active. HTTP loopback fallback is responding."
  printf 'Open: http://127.0.0.1:%s/\n' "$PORT"
else
  fail "Lobby process did not pass its health check. Inspect ~/.node-core/lobby/lobby.log"
fi

COMMITTED=1
info "Installation complete. No Node Core OS install/update/repair operation was executed."
info "Detected environment saved at ~/.node-core/lobby/host-environment.json"
info "Lobby launcher: $SHORTCUT"
