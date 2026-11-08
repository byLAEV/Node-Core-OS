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
ast.parse((profile / "lobby" / "certificate_manager.py").read_text(encoding="utf-8"))
catalog = json.loads((profile / "lobby" / "certificates" / "catalog.json").read_text(encoding="utf-8"))
assert len(catalog["security_profiles"]) == 8
assert catalog["policies"]["independent_from_core"] is True
assert catalog["policies"]["node_identity_private_keys_are_never_managed_by_lobby"] is True
layout = json.loads((profile.parent.parent / "installer" / "layout-manifest.json").read_text(encoding="utf-8"))
assert layout["layout_id"] == "node-core-os-user-runtime"
assert {"app", "bin", "storage", "ipfs", "logs", "runtime", "services", "lobby"} <= {item["path"] for item in layout["directories"]}
manifest = json.loads((profile / "manifest.json").read_text(encoding="utf-8"))
assert manifest["lobby"]["bind"] == "127.0.0.1"
assert manifest["lobby"]["port"] == 8765
assert manifest["lobby"]["transport_preference"] == ["https", "http-loopback"]
assert manifest["lobby"]["release_package_staging"]["enabled"] is True
assert manifest["lobby"]["release_package_staging"]["extracts_archives"] is True
assert manifest["lobby"]["release_package_staging"]["executes_installers"] is True
assert manifest["lobby"]["release_package_staging"]["execution"]["start_endpoint"] == "POST /api/packages/execute"
assert manifest["lobby"]["certificate_manager"]["enabled"] is True
assert manifest["lobby"]["certificate_manager"]["manages_core_p2p_identity_certificate"] is False
html = (profile / "lobby" / "web" / "index.html").read_text(encoding="utf-8")
server = (profile / "lobby" / "server.py").read_text(encoding="utf-8")
assert 'data-panel="termux"' in html
assert "REVEAL COMMANDS" in html
assert "/api/termux/execute" in html and "/api/termux/output" in html
assert "TERMUX_COMMANDS" in server and "shell=False" in server
bootstrap = (profile / "bootstrap-lobby.sh").read_text(encoding="utf-8")
assert "codeload.github.com" in bootstrap
assert "compatibility/termux/install-lobby.sh" in bootstrap
installer = (profile / "install-lobby.sh").read_text(encoding="utf-8")
assert "layout-manifest.json" in installer
filesystem = (profile.parent.parent / "installer" / "lib" / "filesystem.sh").read_text(encoding="utf-8")
assert "layout-manifest.json" in filesystem and "prepare_filesystem" in filesystem
assert "NODE_CORE_LOBBY_REF" in bootstrap
assert "/api/packages/execute" in server and "/api/packages/output" in server
assert "start_official_installer" in server and "_verified_installer_root" in server
assert "EJECUTAR " in html and "INSTALADOR" in html and "pollInstallerJob" in html
assert "execute-package" in html and "api/packages/status" in html
assert "EJECUTAR INSTALADOR OFICIAL" in html and "EJECUTAR ACTUALIZADOR OFICIAL" in html
assert "DESCARGAR Y VERIFICAR PAQUETE" in html
assert "This step only downloads and verifies the archive" not in html
assert "execute.disabled=false" in html
assert "OPEN NODE CORE OS" in html and "openNodeCoreTerminal" in html
assert "/api/terminal/start" in html and "/api/terminal/input" in html
assert "/api/terminal/output" in html and "/api/terminal/close" in html
assert "pty.openpty()" in server and "NODE_CORE_SERVER" in server
assert 'NODE_CORE_SERVER = NODE_CORE_LOBBY_DIR / "server.py"' in server
assert 'cd "$HOME/Node-Core-OS-Lobby" && python server.py' in server
assert 'cd "$HOME/Node-Core-OS-Lobby" && python server.py' in html
assert 'shell=False' in server and 'start_new_session=True' in server
assert "newer than the latest official stable release" in server and "verified as " in server
assert "installer/install.sh" not in bootstrap
print("Python syntax, manifest and bootstrap contract: PASS")
PY

printf '[TEST] Local HTTPS/HTTP server integration\n'
python "$PROFILE/tests/test_server.py" "$PROFILE/lobby/server.py"
python "$PROFILE/tests/test_release_metadata.py"
python "$PROFILE/tests/test_certificate_manager.py"

printf '\nAll Termux Lobby checks passed.\n'
