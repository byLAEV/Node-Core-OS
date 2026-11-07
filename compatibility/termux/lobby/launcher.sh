#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BASE="$HOME/.node-core/lobby"
SERVER="$BASE/server.py"
LOG="$BASE/lobby.log"
mkdir -p "$BASE"
if [[ ! -f "$SERVER" ]]; then
  printf 'Node Core Lobby server is not installed at %s\n' "$SERVER" >&2
  exit 1
fi
if ! pgrep -f "$SERVER" >/dev/null 2>&1; then
  nohup python "$SERVER" >>"$LOG" 2>&1 </dev/null &
fi
for _ in $(seq 1 30); do
  if curl -kfsS "https://127.0.0.1:8765/health" >/dev/null 2>&1 || curl -fsS "http://127.0.0.1:8765/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if curl -kfsS "https://127.0.0.1:8765/health" >/dev/null 2>&1; then
  URL="https://127.0.0.1:8765/"
elif curl -fsS "http://127.0.0.1:8765/health" >/dev/null 2>&1; then
  URL="http://127.0.0.1:8765/"
else
  printf 'Lobby did not become ready. Inspect %s\n' "$LOG" >&2
  exit 1
fi
if command -v termux-open-url >/dev/null 2>&1; then
  termux-open-url "$URL"
else
  printf 'Open this address in the Android browser: %s\n' "$URL"
fi
