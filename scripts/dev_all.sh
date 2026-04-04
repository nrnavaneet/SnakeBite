#!/usr/bin/env bash
# Start local API + HTTPS tunnels (phone) + Flutter web-server, after cleaning scratch files.
# macOS: optionally opens Terminal.app with tail -f on all logs.
#
# Usage (from repo root):
#   bash scripts/dev_all.sh
#   bash scripts/dev_all.sh --no-tunnels     # API + Flutter only (LAN / localhost)
#   bash scripts/dev_all.sh --no-flutter     # API + tunnels only
#   bash scripts/dev_all.sh --no-terminals    # do not open Terminal for log tail
#   bash scripts/dev_all.sh --debug-web      # huge/slow JS (debug) — only for hot reload; default is --release for phone
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-37555}"
RUN_TUNNELS=1
RUN_FLUTTER=1
OPEN_TERMINALS=1
# release = small minified bundle; debug = slow over tunnel (large unoptimized JS)
FLUTTER_WEB_PROFILE="release"

for arg in "$@"; do
  case "$arg" in
    --no-tunnels) RUN_TUNNELS=0 ;;
    --no-flutter) RUN_FLUTTER=0 ;;
    --no-terminals) OPEN_TERMINALS=0 ;;
    --debug-web) FLUTTER_WEB_PROFILE="debug" ;;
    -h|--help)
      grep '^#' "$0" | head -24 | sed 's/^# \{0,1\}//'
      exit 0
      ;;
  esac
done

log() { printf '%s\n' "$*"; }

die() { log "ERROR: $*"; exit 1; }

# --- 1) Scratch / stale dev files ---
clean_scratch() {
  log "Cleaning scratch files…"
  rm -f "$ROOT/models/_upload_tmp.jpg"
  rm -f /tmp/snakebite_api.log /tmp/snakebite_api.pid
  rm -f /tmp/snakebite_tunnel_api.log /tmp/snakebite_tunnel_api.pid
  rm -f /tmp/snakebite_flutter_web.log /tmp/snakebite_flutter_web.pid
  rm -f /tmp/snakebite_tunnel_web.log /tmp/snakebite_tunnel_web.pid
  rm -f /tmp/snakebite_dev_all_urls.txt
  log "  removed upload temp, /tmp/snakebite_* logs+pids"
}

# --- 2) Stop listeners on our ports (old uvicorn / flutter / tunnels) ---
free_ports() {
  log "Freeing ports ${API_PORT}, ${WEB_PORT}, 8090 (if in use)…"
  for p in "${API_PORT}" "${WEB_PORT}" 8090; do
    lsof -ti ":$p" 2>/dev/null | xargs kill -9 2>/dev/null || true
  done
  sleep 0.5
}

UVICORN_BIN="$ROOT/.venv/bin/uvicorn"
if [[ ! -x "$UVICORN_BIN" ]]; then
  UVICORN_BIN=""
  command -v uvicorn >/dev/null 2>&1 || die "uvicorn not found — create .venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
fi

# --- 3) API ---
start_api() {
  log "Starting API on 0.0.0.0:${API_PORT}…"
  if [[ -n "$UVICORN_BIN" ]]; then
    nohup "$UVICORN_BIN" backend.main:app --reload --host 0.0.0.0 --port "${API_PORT}" \
      >> /tmp/snakebite_api.log 2>&1 &
  else
    nohup uvicorn backend.main:app --reload --host 0.0.0.0 --port "${API_PORT}" \
      >> /tmp/snakebite_api.log 2>&1 &
  fi
  echo $! > /tmp/snakebite_api.pid
  for _ in $(seq 1 40); do
    if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
      log "  API healthy."
      return 0
    fi
    sleep 0.25
  done
  die "API did not become healthy — see /tmp/snakebite_api.log"
}

wait_for_tunnel_url() {
  local logfile="$1"
  local url=""
  for _ in $(seq 1 60); do
    url=$(grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "$logfile" 2>/dev/null | head -1 || true)
    if [[ -n "$url" ]]; then
      echo "$url"
      return 0
    fi
    sleep 0.3
  done
  echo ""
}

# --- 4) Tunnels (cloudflared preferred) ---
API_PUBLIC_URL=""

start_tunnel_api() {
  command -v cloudflared >/dev/null 2>&1 || return 1
  log "Starting Cloudflare tunnel → http://127.0.0.1:${API_PORT}…"
  nohup cloudflared tunnel --url "http://127.0.0.1:${API_PORT}" \
    >> /tmp/snakebite_tunnel_api.log 2>&1 &
  echo $! > /tmp/snakebite_tunnel_api.pid
  API_PUBLIC_URL="$(wait_for_tunnel_url /tmp/snakebite_tunnel_api.log)"
  if [[ -z "$API_PUBLIC_URL" ]]; then
    log "  (Could not parse trycloudflare URL yet — check /tmp/snakebite_tunnel_api.log)"
  else
    log "  Public API URL: $API_PUBLIC_URL"
  fi
  return 0
}

start_tunnel_ngrok_api() {
  command -v ngrok >/dev/null 2>&1 || return 1
  log "Starting ngrok → ${API_PORT}…"
  nohup ngrok http "${API_PORT}" --log=stdout >> /tmp/snakebite_tunnel_api.log 2>&1 &
  echo $! > /tmp/snakebite_tunnel_api.pid
  log "  ngrok running — open http://127.0.0.1:4040 for the public URL, or read /tmp/snakebite_tunnel_api.log"
  API_PUBLIC_URL=""
  return 0
}

start_flutter_web() {
  local api_base="$1"
  [[ -z "$api_base" ]] && api_base="http://127.0.0.1:${API_PORT}"
  command -v flutter >/dev/null 2>&1 || { log "  flutter not in PATH — skipping web server."; return 1; }
  cd "$ROOT/mobile/snakebite_rx"
  flutter pub get >> /tmp/snakebite_flutter_web.log 2>&1 || true

  local -a flutter_args=(
    run -d web-server
    --web-hostname 0.0.0.0
    --web-port "${WEB_PORT}"
    --dart-define="API_BASE=${api_base}"
  )
  if [[ "$FLUTTER_WEB_PROFILE" == "release" ]]; then
    flutter_args+=(--release)
    # Avoid pulling CanvasKit/Skwasm from Google CDN over a slow tunnel (first paint faster on phones).
    flutter_args+=(--no-web-resources-cdn)
    log "Starting Flutter web :${WEB_PORT} (release, local web assets — much faster than debug over tunnel; first compile can take a few minutes)…"
  else
    log "Starting Flutter web :${WEB_PORT} (debug — large/slow over tunnel; use only for hot reload)…"
  fi

  nohup flutter "${flutter_args[@]}" >> /tmp/snakebite_flutter_web.log 2>&1 &
  echo $! > /tmp/snakebite_flutter_web.pid
  cd "$ROOT"

  local max_wait=420
  [[ "$FLUTTER_WEB_PROFILE" == "release" ]] || max_wait=120
  local i=0
  while [[ $i -lt $max_wait ]]; do
    if curl -sf "http://127.0.0.1:${WEB_PORT}/" >/dev/null 2>&1; then
      log "  Flutter web responding on http://127.0.0.1:${WEB_PORT}"
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  log "  Flutter may still be compiling — see /tmp/snakebite_flutter_web.log (waited ${max_wait}s)"
}

start_tunnel_web() {
  command -v cloudflared >/dev/null 2>&1 || return 1
  log "Starting Cloudflare tunnel → http://127.0.0.1:${WEB_PORT}…"
  nohup cloudflared tunnel --url "http://127.0.0.1:${WEB_PORT}" \
    >> /tmp/snakebite_tunnel_web.log 2>&1 &
  echo $! > /tmp/snakebite_tunnel_web.pid
  local wurl
  wurl="$(wait_for_tunnel_url /tmp/snakebite_tunnel_web.log)"
  if [[ -n "$wurl" ]]; then
    log "  Public web URL: $wurl"
  else
    log "  (Parse URL from /tmp/snakebite_tunnel_web.log when ready.)"
  fi
}

write_summary() {
  local f="/tmp/snakebite_dev_all_urls.txt"
  {
    echo "SnakeBite dev_all — $(date -Iseconds)"
    echo "API local:    http://127.0.0.1:${API_PORT}"
    [[ -n "$API_PUBLIC_URL" ]] && echo "API public:   $API_PUBLIC_URL"
    echo "Flutter web:  http://127.0.0.1:${WEB_PORT}"
    if [[ -f /tmp/snakebite_tunnel_web.log ]]; then
      grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' /tmp/snakebite_tunnel_web.log 2>/dev/null | head -1 \
        | sed 's/^/Web public:  /' || true
    fi
    echo ""
    echo "Logs: tail -f /tmp/snakebite_api.log /tmp/snakebite_tunnel_api.log /tmp/snakebite_flutter_web.log /tmp/snakebite_tunnel_web.log"
  } | tee "$f"
  log "Summary written to $f"
}

open_log_terminal_macos() {
  [[ "$(uname -s)" == "Darwin" ]] || return 0
  [[ "$OPEN_TERMINALS" == 1 ]] || return 0
  touch /tmp/snakebite_api.log /tmp/snakebite_tunnel_api.log /tmp/snakebite_flutter_web.log /tmp/snakebite_tunnel_web.log
  osascript <<'EOF'
tell application "Terminal"
    activate
    do script "echo 'SnakeBite dev logs (Ctrl+C stops tail only — servers keep running)'; echo ''; tail -f /tmp/snakebite_api.log /tmp/snakebite_tunnel_api.log /tmp/snakebite_flutter_web.log /tmp/snakebite_tunnel_web.log"
end tell
EOF
}

# --- run ---
clean_scratch
free_ports
start_api

API_BASE_FOR_FLUTTER="http://127.0.0.1:${API_PORT}"

if [[ "$RUN_TUNNELS" == 1 ]]; then
  if start_tunnel_api; then
    :
  elif start_tunnel_ngrok_api; then
    :
  else
    log "No cloudflared/ngrok — tunnels skipped. Install: brew install cloudflared"
  fi
  if [[ -n "$API_PUBLIC_URL" ]]; then
    API_BASE_FOR_FLUTTER="$API_PUBLIC_URL"
  fi
fi

if [[ "$RUN_FLUTTER" == 1 ]]; then
  start_flutter_web "$API_BASE_FOR_FLUTTER" || true
  if [[ "$RUN_TUNNELS" == 1 ]] && [[ -f /tmp/snakebite_flutter_web.pid ]]; then
    if command -v cloudflared >/dev/null 2>&1; then
      sleep 2
      start_tunnel_web || true
    fi
  fi
fi

write_summary
log ""
log "Done. PIDs: api=$(cat /tmp/snakebite_api.pid 2>/dev/null || echo '?')"
[[ -f /tmp/snakebite_tunnel_api.pid ]] && log "       tunnel-api=$(cat /tmp/snakebite_tunnel_api.pid)"
[[ -f /tmp/snakebite_flutter_web.pid ]] && log "       flutter-web=$(cat /tmp/snakebite_flutter_web.pid)"
[[ -f /tmp/snakebite_tunnel_web.pid ]] && log "       tunnel-web=$(cat /tmp/snakebite_tunnel_web.pid)"

if [[ "$(uname -s)" == "Darwin" ]] && [[ "$OPEN_TERMINALS" == 1 ]]; then
  open_log_terminal_macos || log "(Could not open Terminal for logs — run: tail -f /tmp/snakebite_*.log)"
fi

log ""
log "Stop everything:"
log "  lsof -ti :${API_PORT} :${WEB_PORT} | xargs kill -9 2>/dev/null; rm -f /tmp/snakebite_*.pid"
