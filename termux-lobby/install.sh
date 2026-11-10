#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
APP_DIR="$HOME/.node-core/lobby"
BIN_DIR="$PREFIX/bin"
mkdir -p "$APP_DIR"
cp "$(dirname "$0")/server.py" "$APP_DIR/server.py"
cp "$(dirname "$0")/index.html" "$APP_DIR/index.html"
cat > "$BIN_DIR/node-lobby" <<'LAUNCH'
#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
APP_DIR="$HOME/.node-core/lobby"
LOG="$APP_DIR/lobby.log"
if ! command -v python >/dev/null 2>&1; then
  echo "Python no está instalado. Instálalo con: pkg install python"
  exit 1
fi
if curl -fsS http://127.0.0.1:8765/health >/dev/null 2>&1; then
  echo "NODE CORE OS Lobby ya está activo: http://127.0.0.1:8765/"
else
  nohup python "$APP_DIR/server.py" >>"$LOG" 2>&1 </dev/null &
  for attempt in $(seq 1 20); do
    if curl -fsS http://127.0.0.1:8765/health >/dev/null 2>&1; then break; fi
    sleep 1
  done
  if ! curl -fsS http://127.0.0.1:8765/health >/dev/null 2>&1; then
    echo "No se pudo iniciar el Lobby. Registro: $LOG"
    exit 1
  fi
  echo "NODE CORE OS Lobby iniciado."
fi
termux-open-url http://127.0.0.1:8765/ >/dev/null 2>&1 || true
LAUNCH
chmod 700 "$BIN_DIR/node-lobby"
echo "Instalación exclusiva del Lobby completada."
"$BIN_DIR/node-lobby"
