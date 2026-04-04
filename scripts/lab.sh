#!/usr/bin/env bash
# Lab UI + public tunnel — kills prior SnakeBite/tunnel processes, starts fresh, opens **HTTPS tunnel** URLs.
#
# Usage (repo root):  make lab   |   bash scripts/lab.sh
# Env: API_PORT (default 8000), WEB_PORT (for port cleanup, default 37555). LAB_OPEN=0 skips browser.
#      LAB_OPEN_DELAY_SEC (default 10) — wait before opening URL so tunnel + page can warm up.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-37555}"

log() { printf '%s\n' "$*"; }
die() { log "ERROR: $*"; exit 1; }

kill_snakebite_pids() {
  log "→ Stopping previous SnakeBite / tunnel / Flutter processes…"
  for f in /tmp/snakebite_api.pid /tmp/snakebite_tunnel_api.pid /tmp/snakebite_flutter_web.pid /tmp/snakebite_tunnel_web.pid \
    /tmp/snakebite_lab_api.pid /tmp/snakebite_lab_tunnel.pid; do
    if [[ -f "$f" ]]; then
      pid=$(cat "$f" 2>/dev/null || true)
      [[ -n "${pid:-}" ]] && kill -9 "$pid" 2>/dev/null || true
    fi
  done
  sleep 0.4
}

free_ports() {
  log "→ Freeing ports ${API_PORT}, ${WEB_PORT}, 8090…"
  for p in "${API_PORT}" "${WEB_PORT}" 8090; do
    lsof -ti ":$p" 2>/dev/null | xargs kill -9 2>/dev/null || true
  done
  sleep 0.4
}

clean_lab_scratch() {
  rm -f "$ROOT/models/_upload_tmp.jpg"
  rm -f /tmp/snakebite_lab_api.log /tmp/snakebite_lab_api.pid
  rm -f /tmp/snakebite_lab_tunnel.log /tmp/snakebite_lab_tunnel.pid
  rm -f /tmp/snakebite_lab_urls.txt
}

api_healthy() {
  curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1
}

UVICORN_BIN="$ROOT/.venv/bin/uvicorn"
if [[ ! -x "$UVICORN_BIN" ]]; then
  UVICORN_BIN=""
  command -v uvicorn >/dev/null 2>&1 || die "uvicorn not found — run: make setup"
fi

wait_for_tunnel_url() {
  local logfile="$1"
  local url=""
  for _ in $(seq 1 100); do
    url=$(grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "$logfile" 2>/dev/null | head -1 || true)
    if [[ -n "$url" ]]; then
      echo "$url"
      return 0
    fi
    sleep 0.25
  done
  echo ""
}

# ngrok local API (https://ngrok.com/docs/agent/api) — first HTTPS tunnel URL
wait_for_ngrok_public_url() {
  local url=""
  for _ in $(seq 1 60); do
    url=$(
      curl -sf http://127.0.0.1:4040/api/tunnels 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    for t in d.get('tunnels') or []:
        u = (t.get('public_url') or '').strip()
        if u.startswith('https://'):
            print(u)
            sys.exit(0)
except Exception:
    pass
" 2>/dev/null || true
    )
    if [[ -n "$url" ]]; then
      echo "$url"
      return 0
    fi
    sleep 0.5
  done
  echo ""
}

start_api_background() {
  log "→ Starting API on 0.0.0.0:${API_PORT} …"
  if [[ -n "$UVICORN_BIN" ]]; then
    nohup "$UVICORN_BIN" backend.main:app --reload --host 0.0.0.0 --port "${API_PORT}" \
      >>/tmp/snakebite_lab_api.log 2>&1 &
  else
    nohup uvicorn backend.main:app --reload --host 0.0.0.0 --port "${API_PORT}" \
      >>/tmp/snakebite_lab_api.log 2>&1 &
  fi
  echo $! >/tmp/snakebite_lab_api.pid
  for _ in $(seq 1 80); do
    if api_healthy; then
      log "  API healthy (pid $(cat /tmp/snakebite_lab_api.pid))"
      return 0
    fi
    sleep 0.25
  done
  die "API did not start — see /tmp/snakebite_lab_api.log"
}

start_tunnel_background() {
  rm -f /tmp/snakebite_lab_tunnel.log
  if command -v cloudflared >/dev/null 2>&1; then
    log "→ Starting Cloudflare tunnel → http://127.0.0.1:${API_PORT} …"
    nohup cloudflared tunnel --url "http://127.0.0.1:${API_PORT}" \
      >>/tmp/snakebite_lab_tunnel.log 2>&1 &
    echo $! >/tmp/snakebite_lab_tunnel.pid
    return 0
  fi
  if command -v ngrok >/dev/null 2>&1; then
    log "→ Starting ngrok → ${API_PORT} …"
    nohup ngrok http "${API_PORT}" --log=stdout >>/tmp/snakebite_lab_tunnel.log 2>&1 &
    echo $! >/tmp/snakebite_lab_tunnel.pid
    return 0
  fi
  die "Install cloudflared (brew install cloudflared) or ngrok for a public URL."
}

# --- main ---
log "SnakeBiteRx — lab + tunnel (clean restart)"
log ""

kill_snakebite_pids
free_ports
clean_lab_scratch

start_api_background

LOCAL_LAB="http://127.0.0.1:${API_PORT}/ui/lab.html"
LOCAL_UI="http://127.0.0.1:${API_PORT}/ui/"
DOCS="http://127.0.0.1:${API_PORT}/docs"

start_tunnel_background
PUBLIC_URL=""
if command -v cloudflared >/dev/null 2>&1; then
  PUBLIC_URL="$(wait_for_tunnel_url /tmp/snakebite_lab_tunnel.log)"
elif command -v ngrok >/dev/null 2>&1; then
  PUBLIC_URL="$(wait_for_ngrok_public_url)"
fi

log ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log " Local"
log "   Lab:   $LOCAL_LAB"
log "   UI:    $LOCAL_UI"
log "   Docs:  $DOCS"
if [[ -n "$PUBLIC_URL" ]]; then
  log ""
  log " Public (HTTPS)"
  log "   Lab:   ${PUBLIC_URL}/ui/lab.html"
  log "   API:   ${PUBLIC_URL}"
else
  log ""
  log " (No public URL yet — cloudflared: tail /tmp/snakebite_lab_tunnel.log; ngrok: http://127.0.0.1:4040 )"
fi
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log ""
log "Logs:  tail -f /tmp/snakebite_lab_tunnel.log"
log "       tail -f /tmp/snakebite_lab_api.log"
log ""
log "Stop:  kill \$(cat /tmp/snakebite_lab_tunnel.pid 2>/dev/null) 2>/dev/null; kill \$(cat /tmp/snakebite_lab_api.pid 2>/dev/null) 2>/dev/null"

{
  echo "SnakeBiteRx make lab — $(date -Iseconds 2>/dev/null || date)"
  echo "local_lab=$LOCAL_LAB"
  [[ -n "$PUBLIC_URL" ]] && echo "public_base=$PUBLIC_URL" && echo "public_lab=${PUBLIC_URL}/ui/lab.html"
} | tee /tmp/snakebite_lab_urls.txt

# Auto-open **tunnel** HTTPS URL (fallback: local only if no public URL yet)
OPEN_URL="$LOCAL_LAB"
[[ -n "$PUBLIC_URL" ]] && OPEN_URL="${PUBLIC_URL}/ui/lab.html"

if [[ "${LAB_OPEN:-1}" != "0" ]]; then
  _delay="${LAB_OPEN_DELAY_SEC:-10}"
  log ""
  log "→ Waiting ${_delay}s for tunnel/page to be ready, then opening browser…"
  sleep "$_delay"
  log "→ Opening: $OPEN_URL"
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import webbrowser; webbrowser.open('$OPEN_URL')" 2>/dev/null || true
  elif [[ "$(uname -s)" == Darwin ]]; then
    open "$OPEN_URL" 2>/dev/null || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$OPEN_URL" 2>/dev/null || true
  fi
fi
