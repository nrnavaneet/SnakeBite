#!/usr/bin/env bash
# Expose a local HTTP port to the public internet (phone / remote QA).
# Requires: cloudflared (recommended) or ngrok — install one:
#   brew install cloudflared
#   brew install ngrok/ngrok/ngrok
#
# Usage:
#   ./scripts/dev_tunnel.sh           # tunnel http://127.0.0.1:8000 (API)
#   ./scripts/dev_tunnel.sh 37555     # tunnel Flutter web-server port
#
# After the URL prints:
#   • Flutter app:  flutter run --dart-define=API_BASE=https://<host>
#   • Or edit mobile/snakebite_rx/web/api_config.json "apiBase" for web builds.
#   • Phone browser: open the same URL as the tunnel if you tunneled the web port.
set -euo pipefail
PORT="${1:-8000}"
TARGET="http://127.0.0.1:${PORT}"

if command -v cloudflared >/dev/null 2>&1; then
  echo "→ Cloudflare quick tunnel → ${TARGET}"
  echo "  (Paste the https://….trycloudflare.com URL into Settings / API_BASE.)"
  exec cloudflared tunnel --url "${TARGET}"
fi

if command -v ngrok >/dev/null 2>&1; then
  echo "→ ngrok → ${TARGET}"
  exec ngrok http "${PORT}"
fi

echo "No tunnel CLI found. Install one of:"
echo "  brew install cloudflared"
echo "  brew install ngrok/ngrok/ngrok"
exit 1
