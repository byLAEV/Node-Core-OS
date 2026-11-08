#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PROFILE="$ROOT/compatibility/termux"

printf '[TEST] Bash syntax\n'
bash -n "$PROFILE/bootstrap-lobby.sh"
bash -n "$PROFILE/install-lobby.sh"
bash -n "$PROFILE/lobby/launcher.sh"
bash "$PROFILE/bootstrap-lobby.sh" --help >/dev/null

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
assert manifest["lobby"]["release_package_staging"]["enabled"] is True
assert manifest["lobby"]["release_package_staging"]["extracts_archives"] is False
assert manifest["lobby"]["release_package_staging"]["executes_installers"] is False
bootstrap = (profile / "bootstrap-lobby.sh").read_text(encoding="utf-8")
assert "codeload.github.com" in bootstrap
assert "compatibility/termux/install-lobby.sh" in bootstrap
assert "NODE_CORE_LOBBY_REF" in bootstrap
assert "installer/install.sh" not in bootstrap
print("Python syntax, manifest and bootstrap contract: PASS")
PY

printf '[TEST] Local HTTPS/HTTP server integration\n'
python "$PROFILE/tests/test_server.py" "$PROFILE/lobby/server.py"
python "$PROFILE/tests/test_release_metadata.py"
python "$PROFILE/tests/test_certificate_manager.py"

printf '\nAll Termux Lobby checks passed.\n'
