#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BASE="$HOME/.node-core/lobby"
SERVER="$BASE/server.py"
LOG="$BASE/lobby.log"
PIDFILE="$BASE/server.pid"
PORT=8765
mkdir -p "$BASE"
if [[ ! -f "$SERVER" ]]; then
  printf 'Node Core Lobby server is not installed at %s\n' "$SERVER" >&2
  exit 1
fi

# Stop any previous Lobby process using this exact installed server path.
# This also upgrades processes started before PID-file support was added.
for proc in /proc/[0-9]*; do
  [[ -r "$proc/cmdline" ]] || continue
  pid="${proc##*/}"
  [[ "$pid" == "$$" || "$pid" == "$PPID" ]] && continue
  cmdline="$(tr '\0' ' ' < "$proc/cmdline" 2>/dev/null || true)"
  if [[ "$cmdline" == *"$SERVER"* ]]; then
    kill "$pid" 2>/dev/null || true
  fi
done

if [[ -f "$PIDFILE" ]]; then
  old_pid="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [[ "$old_pid" =~ ^[0-9]+$ ]]; then kill "$old_pid" 2>/dev/null || true; fi
  rm -f "$PIDFILE"
fi

# Wait briefly for the old listener to release the port.
for _ in $(seq 1 10); do
  if ! curl -kfsS "https://127.0.0.1:$PORT/health" >/dev/null 2>&1 && ! curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

nohup python "$SERVER" >>"$LOG" 2>&1 </dev/null &
server_pid=$!
printf '%s\n' "$server_pid" > "$PIDFILE"
chmod 600 "$PIDFILE"

URL=""
for _ in $(seq 1 30); do
  if curl -kfsS "https://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    URL="https://127.0.0.1:$PORT/"
    break
  elif curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    URL="http://127.0.0.1:$PORT/"
    break
  fi
  if ! kill -0 "$server_pid" 2>/dev/null; then break; fi
  sleep 1
done
if [[ -z "$URL" ]]; then
  printf 'Lobby did not become ready. Recent log:\n' >&2
  tail -n 40 "$LOG" >&2 || true
  exit 1
fi
printf 'NODE CORE OS Lobby is running: %s\n' "$URL"
if command -v termux-open-url >/dev/null 2>&1; then
  termux-open-url "$URL"
else
  printf 'Open this address in the Android browser: %s\n' "$URL"
fi
