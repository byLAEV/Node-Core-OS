#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
OWNER=byLAEV
REPO=Node-Core-OS
REF="${NODE_CORE_LOBBY_REF:-feature/lindesk-local-lobby}"
fail(){ echo "LOBBY BOOTSTRAP ERROR: $*" >&2; exit 1; }
[[ "$(id -u)" != 0 ]] || fail "Do not run as root."
[[ -n "${HOME:-}" && -d "$HOME" ]] || fail "HOME unavailable."
for c in bash curl python3; do command -v "$c" >/dev/null || fail "Missing $c"; done
python3 - <<'PY' || fail "Expected Debian ARM64."
import platform
from pathlib import Path
d={}
for line in Path("/etc/os-release").read_text().splitlines():
 if "=" in line:
  k,v=line.split("=",1); d[k]=v.strip().strip('"')
assert d.get("ID")=="debian", d.get("ID")
assert platform.machine() in ("aarch64","arm64"), platform.machine()
import venv,ssl
PY
[[ "$REF" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ && "$REF" != *".."* && "$REF" != *"//"* ]] || fail "Invalid ref."
W="$(mktemp -d "$HOME/.node-core-lobby-bootstrap.XXXXXX")"
trap 'rm -rf "$W"' EXIT
ENC="$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=""))' "$REF")"
curl -fsSL --retry 4 --retry-all-errors -H "Accept: application/vnd.github+json" -H "User-Agent: Node-Core-OS-Lobby" "https://api.github.com/repos/$OWNER/$REPO/branches/$ENC" -o "$W/ref.json" || fail "Cannot resolve GitHub ref."
SHA="$(python3 -c 'import json,sys,re; s=json.load(open(sys.argv[1]))["commit"]["sha"]; assert re.fullmatch("[0-9a-f]{40}",s); print(s)' "$W/ref.json")" || fail "Invalid commit SHA."
curl -fsSL --retry 4 --retry-all-errors "https://codeload.github.com/$OWNER/$REPO/tar.gz/$SHA" -o "$W/src.tgz" || fail "Cannot download source."
mkdir "$W/src"
python3 - "$W/src.tgz" "$W/src" <<'PY'
import sys,tarfile,os,shutil
from pathlib import Path,PurePosixPath
dst=Path(sys.argv[2]).resolve()
with tarfile.open(sys.argv[1],"r:gz") as t:
 for m in t.getmembers():
  p=PurePosixPath(m.name)
  if p.is_absolute() or ".." in p.parts: raise SystemExit("Unsafe archive path")
  if not (m.isdir() or m.isfile()): continue
  q=dst.joinpath(*p.parts)
  if os.path.commonpath((str(dst),str(q.resolve())))!=str(dst): raise SystemExit("Archive path escape")
  if m.isdir(): q.mkdir(parents=True,exist_ok=True)
  else:
   q.parent.mkdir(parents=True,exist_ok=True)
   with t.extractfile(m) as a,q.open("xb") as b: shutil.copyfileobj(a,b)
PY
ROOT=""
for p in "$W"/src/Node-Core-OS-*; do [[ -f "$p/compatibility/android/lindesk/install-lobby.sh" ]] && ROOT="$p" && break; done
[[ -n "$ROOT" ]] || fail "LinDesk installer absent in source."
bash "$ROOT/compatibility/android/lindesk/install-lobby.sh"
