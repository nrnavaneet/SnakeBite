#!/usr/bin/env bash
# Serve the Flutter web build (production-like). Run API separately: make api
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB="$ROOT/mobile/snakebite_rx/build/web"
PORT="${PORT:-8090}"
if [[ ! -f "$WEB/index.html" ]]; then
  echo "No web build found. Run first:"
  echo "  make web-build"
  exit 1
fi
cd "$WEB"
echo "SnakeBiteRx Flutter web → http://127.0.0.1:${PORT}"
echo "Ensure the API is running: make api  (http://127.0.0.1:8000)"
echo "Press Ctrl+C to stop."
exec python3 -m http.server "$PORT" --bind 127.0.0.1
