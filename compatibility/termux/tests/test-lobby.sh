#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PROFILE="$ROOT/compatibility/termux"

printf '[TEST] Bash syntax\n'
bash -n "$PROFILE/install-lobby.sh"
bash -n "$PROFILE/lobby/launcher.sh"

printf '[TEST] Python syntax and manifest JSON\n'
python - "$PROFILE" <<'PY'
import ast
import json
import pathlib
import sys

profile = pathlib.Path(sys.argv[1])
ast.parse((profile / "lobby" / "server.py").read_text(encoding="utf-8"))
manifest = json.loads((profile / "manifest.json").read_text(encoding="utf-8"))
assert manifest["lobby"]["bind"] == "127.0.0.1"
assert manifest["lobby"]["port"] == 8765
assert manifest["lobby"]["transport_preference"] == ["https", "http-loopback"]
print("Python syntax and manifest: PASS")
PY

printf '[TEST] Local HTTPS/HTTP server integration\n'
python "$PROFILE/tests/test_server.py" "$PROFILE/lobby/server.py"

printf '\nAll Termux Lobby checks passed.\n'
