#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
umask 077

BASE="$HOME/.node-core/lobby"
SERVER="$BASE/server.py"
LOG="$BASE/lobby.log"
PIDFILE="$BASE/server.pid"
PORT=8765
HOST=127.0.0.1

fail() { printf 'NODE CORE OS Lobby: %s\n' "$*" >&2; exit 1; }

[[ -f "$SERVER" && ! -L "$SERVER" ]] || fail "server.py is not installed at $SERVER"
command -v python >/dev/null 2>&1 || fail "Python is unavailable."
command -v curl >/dev/null 2>&1 || fail "curl is unavailable."
mkdir -p "$BASE"
chmod 700 "$BASE"
touch "$LOG"
chmod 600 "$LOG"

# A process is considered the Lobby only when its argument vector contains
# the exact installed server path. Do not kill processes by loose name match.
is_lobby_process() {
  local pid="$1"
  [[ -r "/proc/$pid/cmdline" ]] || return 1
  tr '\0' '\n' < "/proc/$pid/cmdline" 2>/dev/null | grep -Fxq -- "$SERVER"
}

stop_lobby_process() {
  local pid="$1"
  if is_lobby_process "$pid"; then
    kill "$pid" 2>/dev/null || true
    for _ in {1..10}; do
      is_lobby_process "$pid" || return 0
      sleep 0.2
    done
    if is_lobby_process "$pid"; then
      kill -TERM "$pid" 2>/dev/null || true
      sleep 1
    fi
  fi
}

# Stop the process recorded in the PID file only if it is verifiably this server.
if [[ -f "$PIDFILE" ]]; then
  old_pid="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [[ "$old_pid" =~ ^[0-9]+$ ]]; then
    stop_lobby_process "$old_pid"
  fi
  rm -f "$PIDFILE"
fi

# Also find an older instance that predates PID-file support.
for proc in /proc/[0-9]*; do
  pid="${proc##*/}"
  [[ "$pid" == "$$" || "$pid" == "$PPID" ]] && continue
  if is_lobby_process "$pid"; then
    stop_lobby_process "$pid"
  fi
done

# Wait for the previous listener to release the loopback port.
for _ in {1..20}; do
  if ! curl -kfsS "https://$HOST:$PORT/health" >/dev/null 2>&1 && \
     ! curl -fsS "http://$HOST:$PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

nohup python "$SERVER" >>"$LOG" 2>&1 </dev/null &
server_pid=$!
printf '%s\n' "$server_pid" > "$PIDFILE"
chmod 600 "$PIDFILE"

URL=""
for _ in {1..40}; do
  if curl -kfsS "https://$HOST:$PORT/health" >/dev/null 2>&1; then
    URL="https://$HOST:$PORT/"
    break
  fi
  if curl -fsS "http://$HOST:$PORT/health" >/dev/null 2>&1; then
    URL="http://$HOST:$PORT/"
    break
  fi
  if ! kill -0 "$server_pid" 2>/dev/null; then
    break
  fi
  sleep 0.25
done

if [[ -z "$URL" ]]; then
  rm -f "$PIDFILE"
  printf 'Lobby did not become ready. Recent log output:\n' >&2
  tail -n 50 "$LOG" >&2 || true
  exit 1
fi

printf 'NODE CORE OS Lobby is running: %s\n' "$URL"
if command -v termux-open-url >/dev/null 2>&1; then
  termux-open-url "$URL" || printf 'Open this address manually: %s\n' "$URL"
else
  printf 'Open this address in the Android browser: %s\n' "$URL"
fi
