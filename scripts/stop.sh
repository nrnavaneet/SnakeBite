#!/usr/bin/env bash
# Stop SnakeBite dev stack: API, tunnels, Flutter web, static serve — same PIDs/ports as lab / dev-all.
# Usage (repo root):  make stop   |   bash scripts/stop.sh
# Env: API_PORT (default 8000), WEB_PORT (default 37555)
set -euo pipefail

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-37555}"

log() { printf '%s\n' "$*"; }

log "Stopping SnakeBite processes (PIDs from /tmp/snakebite_*.pid)…"
for f in \
  /tmp/snakebite_api.pid \
  /tmp/snakebite_tunnel_api.pid \
  /tmp/snakebite_flutter_web.pid \
  /tmp/snakebite_tunnel_web.pid \
  /tmp/snakebite_lab_api.pid \
  /tmp/snakebite_lab_tunnel.pid
do
  if [[ -f "$f" ]]; then
    pid=$(cat "$f" 2>/dev/null || true)
    [[ -n "${pid:-}" ]] && kill -9 "$pid" 2>/dev/null || true
  fi
done
sleep 0.4

log "Freeing ports ${API_PORT}, ${WEB_PORT}, 8090 (listeners)…"
for p in "${API_PORT}" "${WEB_PORT}" 8090; do
  lsof -ti ":$p" 2>/dev/null | xargs kill -9 2>/dev/null || true
done
sleep 0.3

log "Removing pid files…"
rm -f \
  /tmp/snakebite_api.pid \
  /tmp/snakebite_tunnel_api.pid \
  /tmp/snakebite_flutter_web.pid \
  /tmp/snakebite_tunnel_web.pid \
  /tmp/snakebite_lab_api.pid \
  /tmp/snakebite_lab_tunnel.pid

log "Done. (Log files under /tmp/snakebite*.log left in place.)"
