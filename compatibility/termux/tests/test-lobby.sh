#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PROFILE="$ROOT/compatibility/termux"

printf '[TEST] Bash syntax\n'
bash -n "$PROFILE/bootstrap-lobby.sh"
bash -n "$PROFILE/install-lobby.sh"
bash -n "$PROFILE/lobby/launcher.sh"
bash "$PROFILE/bootstrap-lobby.sh" --help >/dev/null

printf '[TEST] Lobby JavaScript syntax (when Node.js is available)\n'
if command -v node >/dev/null 2>&1; then
  python - "$PROFILE/lobby/web/index.html" <<'PY'
import pathlib
import re
import subprocess
import sys
import tempfile

html = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
scripts = re.findall(r"<script>(.*?)</script>", html, flags=re.DOTALL)
assert len(scripts) == 1, "Expected exactly one inline Lobby application script"
with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as script:
    script.write(scripts[0])
    script.flush()
    subprocess.run(["node", "--check", script.name], check=True)
print("Lobby JavaScript syntax: PASS")
PY
else
  printf 'Node.js is unavailable; JavaScript syntax check skipped.\\n'
fi

printf '[TEST] Python syntax and manifest JSON\n'
python - "$PROFILE" <<'PY'
import ast
import json
import pathlib
import sys

profile = pathlib.Path(sys.argv[1])
ast.parse((profile / "lobby" / "server.py").read_text(encoding="utf-8"))
ast.parse((profile / "lobby" / "certificate_manager.py").read_text(encoding="utf-8"))
ast.parse((profile / "lobby" / "bitcoin_identity.py").read_text(encoding="utf-8"))
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
for endpoint in ("/api/termux/execute", "/api/termux/output"):
    assert endpoint in html, f"Lobby UI is missing endpoint call: {endpoint}"
    assert f'if path == "{endpoint}"' in server, f"Lobby server is missing endpoint handler: {endpoint}"
assert "TERMUX_COMMANDS" in server and "shell=False" in server
assert "BitcoinIdentityGate" in server
assert 'pending_identity = BITCOIN_IDENTITY.read_pending()' in server
assert 'pending_identity is None' in server
assert 'node-core-os-local-bitcoin-key-control/v1' in server
assert 'First installation is locked' in server
assert "request dictionary even when validation fails" in server
assert "finally:" in server and "payload.clear()" in server
assert "First installation is locked" in server
assert "associate_pending_bitcoin_identity_with_node" in server
assert "NodeIdentityStore" in server and "EntityIdentityRegistry" in server
assert 'data-panel="identity"' in html
assert "/api/identity/bitcoin" in html
assert 'id="bitcoin-private-key"' in html
assert 'id="bitcoin-full-name"' in html
assert 'type="password"' in html
assert "private_key_hex:privateKey" in html
assert "window.location.protocol!=='https:'" in html
assert "refreshBitcoinIdentityHeader" in html
assert 'id="bitcoin-address-header"' in html
assert "associate-bitcoin-identity" in html
assert "/api/identity/bitcoin/associate-node" in html
assert "localStorage.setItem('bitcoin-private-key'" not in html
assert "sessionStorage.setItem('bitcoin-private-key'" not in html
assert "Browser and Python memory cleanup is best-effort" in html
assert manifest["lobby"]["bitcoin_identity"]["enabled"] is True
for endpoint in ("/api/identity/bitcoin", "/api/identity/bitcoin/challenge", "/api/identity/bitcoin/verify", "/api/identity/bitcoin/verify-local-key", "/api/identity/bitcoin/associate-node", "/api/identity/bitcoin/cancel"):
    assert endpoint in server, f"Missing Bitcoin identity endpoint: {endpoint}"
bootstrap = (profile / "bootstrap-lobby.sh").read_text(encoding="utf-8")
assert "codeload.github.com" in bootstrap
assert "compatibility/termux/install-lobby.sh" in bootstrap
installer = (profile / "install-lobby.sh").read_text(encoding="utf-8")
assert "bitcoin_identity.py" in installer
assert "layout-manifest.json" in installer
filesystem = (profile.parent.parent / "installer" / "lib" / "filesystem.sh").read_text(encoding="utf-8")
assert "layout-manifest.json" in filesystem and "prepare_filesystem" in filesystem
assert "NODE_CORE_LOBBY_REF" in bootstrap
assert "/api/packages/execute" in server and "/api/packages/output" in server
assert "start_official_installer" in server and "_verified_installer_root" in server
assert "EJECUTAR " in html and "INSTALADOR" in html and "pollInstallerJob" in html
assert "execute-package" in html and "api/packages/status" in html
# renderRelease() composes the visible button label from the selected operation.
# Validate the mapping and template expression rather than searching for a
# fully-rendered phrase that does not exist literally in the source HTML.
assert "const actionName=mode==='install'?'INSTALADOR':'ACTUALIZADOR';" in html
assert "+actionName+' OFICIAL</button>" in html
assert "DESCARGAR Y VERIFICAR PAQUETE" in html
assert "This step only downloads and verifies the archive" not in html
assert "execute.disabled=false" in html
assert "OPEN NODE CORE OS" in html and "openNodeCoreTerminal" in html
assert "/api/terminal/start" in html and "/api/terminal/input" in html
assert "/api/terminal/output" in html and "/api/terminal/close" in html
assert "pty.openpty()" in server and "NODE_CORE_MAIN" in server
assert 'NODE_CORE_MAIN = NODE_CORE_OS_DIR / "main.py"' in server
assert 'NODE_CORE_LAUNCHER = HOME / ".node-core" / "bin" / "node-core"' in server
assert 'if NODE_CORE_LAUNCHER.is_file():' in server
assert 'command = \'"$HOME/.node-core/bin/node-core"\'' in server
assert 'elif NODE_CORE_MAIN.is_file():' in server
assert 'cd "$HOME/Node-Core-OS" && python main.py' in server
assert 'cd "$HOME/Node-Core-OS" && python main.py' in html
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
